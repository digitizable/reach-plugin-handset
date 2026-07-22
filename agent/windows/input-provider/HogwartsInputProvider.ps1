#Requires -Version 5.1
<#
.SYNOPSIS
  High-IL Keepstream input helper — hogwarts-input/1 over a named pipe.

.DESCRIPTION
  Listens on \\.\pipe\hogwarts-input (or -PipeName), reads HELLO + JSON event
  batches from the Medium agent, and injects via user32 SendInput.

  This is NOT a UAC bypass. Run this script elevated once (or via a Highest
  scheduled task installed by install-input-provider-task.ps1) so it can drive
  Task Manager / admin UI. The agent stays Medium and only forwards INPUT.

.PARAMETER PipeName
  Named pipe leaf name (default hogwarts-input).

.PARAMETER Once
  Exit after the first client disconnects (default: re-arm for next Session).
#>
param(
    [string]$PipeName = "hogwarts-input",
    [switch]$Once
)

$ErrorActionPreference = "Stop"

# --- SendInput via C# ---
$sendInputSrc = @"
using System;
using System.Runtime.InteropServices;

public static class HogwartsInject {
  [StructLayout(LayoutKind.Sequential)]
  public struct MOUSEINPUT {
    public int dx, dy;
    public uint mouseData, dwFlags, time;
    public IntPtr dwExtraInfo;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct KEYBDINPUT {
    public ushort wVk, wScan;
    public uint dwFlags, time;
    public IntPtr dwExtraInfo;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct HARDWAREINPUT {
    public uint uMsg;
    public ushort wParamL, wParamH;
  }
  [StructLayout(LayoutKind.Explicit)]
  public struct INPUTUNION {
    [FieldOffset(0)] public MOUSEINPUT mi;
    [FieldOffset(0)] public KEYBDINPUT ki;
    [FieldOffset(0)] public HARDWAREINPUT hi;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct INPUT {
    public uint type;
    public INPUTUNION U;
  }
  [DllImport("user32.dll", SetLastError=true)]
  public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
  [DllImport("user32.dll")]
  public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")]
  public static extern short VkKeyScanW(char ch);
  [DllImport("user32.dll")]
  public static extern int GetSystemMetrics(int nIndex);

  const uint INPUT_MOUSE = 0, INPUT_KEYBOARD = 1;
  const uint MOUSEEVENTF_MOVE = 0x0001, MOUSEEVENTF_ABSOLUTE = 0x8000;
  const uint MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004;
  const uint MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_RIGHTUP = 0x0010;
  const uint MOUSEEVENTF_MIDDLEDOWN = 0x0020, MOUSEEVENTF_MIDDLEUP = 0x0040;
  const uint MOUSEEVENTF_WHEEL = 0x0800, MOUSEEVENTF_HWHEEL = 0x1000;
  const uint KEYEVENTF_KEYUP = 0x0002;

  static int ScreenW() { return Math.Max(1, GetSystemMetrics(0) - 1); }
  static int ScreenH() { return Math.Max(1, GetSystemMetrics(1) - 1); }

  static void Mouse(uint flags, int? x, int? y) {
    var inp = new INPUT();
    inp.type = INPUT_MOUSE;
    if (x.HasValue && y.HasValue) {
      int sx = ScreenW(), sy = ScreenH();
      int ax = (int)(Math.Max(0, Math.Min(sx, x.Value)) * 65535.0 / sx);
      int ay = (int)(Math.Max(0, Math.Min(sy, y.Value)) * 65535.0 / sy);
      inp.U.mi = new MOUSEINPUT { dx = ax, dy = ay, dwFlags = flags | MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE };
    } else {
      inp.U.mi = new MOUSEINPUT { dwFlags = flags };
    }
    SendInput(1, new[] { inp }, Marshal.SizeOf(typeof(INPUT)));
  }

  static void MouseRel(int dx, int dy) {
    // Relative move — Roblox Studio camera orbit (no absolute flail)
    if (dx == 0 && dy == 0) return;
    if (dx > 400) dx = 400; if (dx < -400) dx = -400;
    if (dy > 400) dy = 400; if (dy < -400) dy = -400;
    var inp = new INPUT();
    inp.type = INPUT_MOUSE;
    inp.U.mi = new MOUSEINPUT { dx = dx, dy = dy, dwFlags = MOUSEEVENTF_MOVE };
    SendInput(1, new[] { inp }, Marshal.SizeOf(typeof(INPUT)));
  }

  static void Wheel(int notches, bool horizontal) {
    if (notches == 0) return;
    if (notches > 20) notches = 20;
    if (notches < -20) notches = -20;
    var inp = new INPUT();
    inp.type = INPUT_MOUSE;
    // mouseData is DWORD; cast signed wheel ticks * 120
    uint data = unchecked((uint)(notches * 120));
    inp.U.mi = new MOUSEINPUT {
      mouseData = data,
      dwFlags = horizontal ? MOUSEEVENTF_HWHEEL : MOUSEEVENTF_WHEEL
    };
    SendInput(1, new[] { inp }, Marshal.SizeOf(typeof(INPUT)));
  }

  [DllImport("user32.dll")]
  public static extern uint MapVirtualKey(uint uCode, uint uMapType);

  const uint KEYEVENTF_EXTENDEDKEY = 0x0001, KEYEVENTF_SCANCODE = 0x0008;

  static void Key(ushort vk, bool up) {
    // Scan-code inject — games (Roblox etc.) need holds via scancodes
    uint scan = MapVirtualKey(vk, 0 /* MAPVK_VK_TO_VSC */) & 0xFF;
    uint flags = up ? KEYEVENTF_KEYUP : 0;
    // Extended keys: arrows, insert/delete/home/end/pgup/pgdn, Win
    if (vk == 0x21 || vk == 0x22 || vk == 0x23 || vk == 0x24 ||
        vk == 0x25 || vk == 0x26 || vk == 0x27 || vk == 0x28 ||
        vk == 0x2D || vk == 0x2E || vk == 0x5B || vk == 0x5C) {
      flags |= KEYEVENTF_EXTENDEDKEY;
    }
    var inp = new INPUT();
    inp.type = INPUT_KEYBOARD;
    if (scan != 0) {
      flags |= KEYEVENTF_SCANCODE;
      inp.U.ki = new KEYBDINPUT { wVk = 0, wScan = (ushort)scan, dwFlags = flags };
    } else {
      inp.U.ki = new KEYBDINPUT { wVk = vk, dwFlags = flags };
    }
    SendInput(1, new[] { inp }, Marshal.SizeOf(typeof(INPUT)));
  }

  static ushort ResolveVk(string key) {
    if (string.IsNullOrEmpty(key)) return 0;
    string k = key.ToLowerInvariant().Replace("-", "_");
    switch (k) {
      case "return": case "enter": return 0x0D;
      case "escape": case "esc": return 0x1B;
      case "tab": return 0x09;
      case "backspace": return 0x08;
      case "space": return 0x20;
      case "up": return 0x26;
      case "down": return 0x28;
      case "left": return 0x25;
      case "right": return 0x27;
      case "delete": return 0x2E;
      case "home": return 0x24;
      case "end": return 0x23;
      case "page_up": case "prior": return 0x21;
      case "page_down": case "next": return 0x22;
      case "insert": return 0x2D;
      case "shift": return 0x10;
      case "ctrl": case "control": return 0x11;
      case "alt": return 0x12;
      case "super": case "win": return 0x5B;
      default:
        if (k.Length >= 2 && k[0] == 'f') {
          int fn;
          if (int.TryParse(k.Substring(1), out fn) && fn >= 1 && fn <= 12)
            return (ushort)(0x70 + fn - 1);
        }
        if (k.Length == 1) {
          char c = char.ToUpperInvariant(k[0]);
          if (c >= 'A' && c <= 'Z') return (ushort)c;
          if (c >= '0' && c <= '9') return (ushort)c;
          short vk = VkKeyScanW(k[0]);
          if (vk != -1) return (ushort)(vk & 0xFF);
        }
        return 0;
    }
  }

  public static void ApplyEvent(string type, double? fx, double? fy, int? x, int? y, string button, string key, string text) {
    ApplyEventFull(type, fx, fy, x, y, button, key, text, null, 0);
  }

  public static void ApplyEventFull(string type, double? fx, double? fy, int? x, int? y, string button, string key, string text, string mods, int delta) {
    int? px = null, py = null;
    if (fx.HasValue || fy.HasValue) {
      double fxx = fx ?? 0.5, fyy = fy ?? 0.5;
      if (fxx < 0) fxx = 0; if (fxx > 1) fxx = 1;
      if (fyy < 0) fyy = 0; if (fyy > 1) fyy = 1;
      px = (int)(fxx * ScreenW());
      py = (int)(fyy * ScreenH());
    } else if (x.HasValue || y.HasValue) {
      px = x ?? 0; py = y ?? 0;
    }
    string typ = (type ?? "click").ToLowerInvariant();
    if (typ == "rmove" || typ == "rel" || typ == "relative") {
      // dx/dy passed via x/y slots when type is rmove (see Invoke-Events)
      int rdx = x ?? 0, rdy = y ?? 0;
      MouseRel(rdx, rdy);
      return;
    }
    if ((typ == "move" || typ == "click" || typ == "dblclick" || typ == "down" || typ == "up" || typ == "wheel" || typ == "wheel_h" || typ == "hwheel") && px.HasValue && py.HasValue) {
      Mouse(0, px, py);
      SetCursorPos(px.Value, py.Value);
    }
    if (typ == "move") return;
    if (typ == "wheel" || typ == "wheel_h" || typ == "hwheel") {
      int d = delta;
      if (d == 0) d = 0;
      int notch = d > 0 ? 1 : (d < 0 ? -1 : 0);
      if (notch != 0) Wheel(notch, typ == "wheel_h" || typ == "hwheel");
      return;
    }
    uint down = MOUSEEVENTF_LEFTDOWN, upf = MOUSEEVENTF_LEFTUP;
    string btn = (button ?? "left").ToLowerInvariant();
    if (btn == "right") { down = MOUSEEVENTF_RIGHTDOWN; upf = MOUSEEVENTF_RIGHTUP; }
    else if (btn == "middle") { down = MOUSEEVENTF_MIDDLEDOWN; upf = MOUSEEVENTF_MIDDLEUP; }
    if (typ == "down") { Mouse(down, null, null); return; }
    if (typ == "up") { Mouse(upf, null, null); return; }
    if (typ == "dblclick") {
      Mouse(down, null, null); Mouse(upf, null, null);
      Mouse(down, null, null); Mouse(upf, null, null);
      return;
    }
    if (typ == "click") { Mouse(down, null, null); Mouse(upf, null, null); return; }
    if (typ == "type" && !string.IsNullOrEmpty(text)) {
      foreach (char ch in text) {
        if (text.Length > 200) break;
        short vk = VkKeyScanW(ch);
        if (vk == -1) continue;
        ushort code = (ushort)(vk & 0xFF);
        bool shift = ((vk >> 8) & 1) != 0;
        if (shift) Key(0x10, false);
        Key(code, false); Key(code, true);
        if (shift) Key(0x10, true);
      }
      return;
    }
    if ((typ == "key_down" || typ == "keydown" || typ == "key_up" || typ == "keyup") && !string.IsNullOrEmpty(key)) {
      ushort code = ResolveVk(key);
      if (code != 0) Key(code, typ == "key_up" || typ == "keyup");
      return;
    }
    if (typ == "key" && !string.IsNullOrEmpty(key)) {
      ushort code = ResolveVk(key);
      // Optional mods: "ctrl,alt,shift,super"
      var modVks = new System.Collections.Generic.List<ushort>();
      if (!string.IsNullOrEmpty(mods)) {
        foreach (var part in mods.Split(new[] { ',', ' ', '+' }, StringSplitOptions.RemoveEmptyEntries)) {
          var m = part.Trim().ToLowerInvariant();
          if (m == "ctrl" || m == "control" || m == "ctl") modVks.Add(0x11);
          else if (m == "alt" || m == "menu") modVks.Add(0x12);
          else if (m == "shift") modVks.Add(0x10);
          else if (m == "super" || m == "win" || m == "meta" || m == "cmd") modVks.Add(0x5B);
        }
      }
      if (code != 0) {
        foreach (var mv in modVks) Key(mv, false);
        Key(code, false); Key(code, true);
        for (int i = modVks.Count - 1; i >= 0; i--) Key(modVks[i], true);
      }
    }
  }
}
"@

try {
    Add-Type -TypeDefinition $sendInputSrc -Language CSharp -ErrorAction Stop | Out-Null
} catch {
    # type may already exist in session
    if ($_.Exception.Message -notmatch "already exists") { throw }
}

function Write-Log([string]$msg) {
    $ts = (Get-Date).ToString("o")
    [Console]::Error.WriteLine("[hogwarts-input] $ts $msg")
}

function Invoke-Events($obj) {
    if ($null -eq $obj) { return 0 }
    $evs = $obj.events
    if ($null -eq $evs) { return 0 }
    $n = 0
    foreach ($ev in $evs) {
        if ($null -eq $ev) { continue }
        $type = [string]$ev.type
        $fx = $null; $fy = $null; $x = $null; $y = $null
        if ($null -ne $ev.fx) { $fx = [double]$ev.fx }
        if ($null -ne $ev.fy) { $fy = [double]$ev.fy }
        if ($null -ne $ev.x) { $x = [int]$ev.x }
        if ($null -ne $ev.y) { $y = [int]$ev.y }
        $button = [string]$ev.button
        $key = [string]$ev.key
        $text = [string]$ev.text
        $mods = $null
        if ($null -ne $ev.mods) {
            if ($ev.mods -is [System.Array]) { $mods = ($ev.mods -join ",") }
            else { $mods = [string]$ev.mods }
        } elseif ($null -ne $ev.modifiers) {
            if ($ev.modifiers -is [System.Array]) { $mods = ($ev.modifiers -join ",") }
            else { $mods = [string]$ev.modifiers }
        }
        $delta = 0
        if ($null -ne $ev.delta) { try { $delta = [int]$ev.delta } catch { $delta = 0 } }
        elseif ($null -ne $ev.dy -and $type -ne "rmove" -and $type -ne "rel" -and $type -ne "relative") {
            try { $delta = [int]$ev.dy } catch { $delta = 0 }
        }
        elseif ($null -ne $ev.dx -and $type -ne "rmove" -and $type -ne "rel" -and $type -ne "relative") {
            try { $delta = [int]$ev.dx } catch { $delta = 0 }
        }
        # rmove: pass dx/dy through x/y integer slots
        if ($type -eq "rmove" -or $type -eq "rel" -or $type -eq "relative") {
            if ($null -ne $ev.dx) { try { $x = [int]$ev.dx } catch { $x = 0 } }
            if ($null -ne $ev.dy) { try { $y = [int]$ev.dy } catch { $y = 0 } }
        }
        try {
            [HogwartsInject]::ApplyEventFull($type, $fx, $fy, $x, $y, $button, $key, $text, $mods, $delta)
            $n++
        } catch {
            Write-Log "inject error: $($_.Exception.Message)"
        }
    }
    return $n
}

function Handle-Client([System.IO.Pipes.NamedPipeServerStream]$pipe) {
    # Server is In-only: read HELLO + event lines; HELLO_OK is optional for agents.
    $reader = New-Object System.IO.StreamReader($pipe, [Text.Encoding]::UTF8, $false, 4096, $true)
    $hello = $reader.ReadLine()
    if (-not $hello) { return }
    $parts = $hello.Trim() -split "\s+"
    if ($parts.Count -lt 2 -or $parts[0] -ne "HELLO") {
        Write-Log "bad hello: $hello"
        return
    }
    Write-Log "client HELLO ok session=$($parts[2])"
    while ($true) {
        $line = $reader.ReadLine()
        if ($null -eq $line) { break }
        $line = $line.Trim()
        if (-not $line) { continue }
        if ($line.ToUpperInvariant() -eq "BYE") {
            Write-Log "BYE"
            break
        }
        try {
            $obj = $line | ConvertFrom-Json
            $n = Invoke-Events $obj
            if ($n -gt 0) { Write-Log "applied $n event(s)" }
        } catch {
            Write-Log "bad json: $($line.Substring(0, [Math]::Min(80, $line.Length)))"
        }
    }
}

Write-Log "listening \\\\.\\pipe\\$PipeName (elevated inject helper — not a UAC bypass)"
while ($true) {
    $pipe = $null
    try {
        # In-only: clients write HELLO/events; we do not require duplex open.
        # (Write-only CreateFile clients hang against some InOut servers.)
        $pipe = New-Object System.IO.Pipes.NamedPipeServerStream(
            $PipeName,
            [System.IO.Pipes.PipeDirection]::In,
            4,
            [System.IO.Pipes.PipeTransmissionMode]::Byte,
            [System.IO.Pipes.PipeOptions]::None,
            4096,
            4096
        )
        $pipe.WaitForConnection()
        Write-Log "client connected"
        Handle-Client $pipe
    } catch {
        Write-Log "session error: $($_.Exception.Message)"
    } finally {
        if ($pipe) {
            try { $pipe.Dispose() } catch {}
        }
    }
    if ($Once) { break }
    Start-Sleep -Milliseconds 200
}
Write-Log "exit"
