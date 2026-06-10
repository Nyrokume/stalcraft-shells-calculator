from pathlib import Path

p = Path(__file__).resolve().parents[1] / "calculator" / "shells-charts.html"
s = p.read_text(encoding="utf-8")
needle = "if(!f.length)return{labels:"
idx = s.find(needle)
if idx < 0:
    raise SystemExit("needle not found")
end = s.find(";", idx)
line = s[idx:end + 1]
fixed = line.replace("}]}};", "}]};")
if line == fixed:
    raise SystemExit(f"no change in: {line!r}")
s = s[:idx] + fixed + s[end + 1:]
p.write_text(s, encoding="utf-8")
print("fixed")
