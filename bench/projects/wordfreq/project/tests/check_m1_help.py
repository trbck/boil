import subprocess, sys
r = subprocess.run([sys.executable, "-m", "wordfreq", "--help"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
assert "--top" in r.stdout, r.stdout
print("ok")
