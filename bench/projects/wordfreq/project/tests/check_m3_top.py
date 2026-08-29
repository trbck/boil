import subprocess, sys, tempfile, os
d = tempfile.mkdtemp(); f = os.path.join(d, "f.txt")
open(f, "w").write("b a b c a b\n")
r = subprocess.run([sys.executable, "-m", "wordfreq", f, "--top", "2"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
assert r.stdout.splitlines() == ["b 3", "a 2"], f"COUNTEREXAMPLE: got {r.stdout.splitlines()!r}"
print("ok")
