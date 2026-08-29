import subprocess, sys, tempfile, os
d = tempfile.mkdtemp(); f = os.path.join(d, "f.txt")
open(f, "w").write("b a B c a b\n")
r = subprocess.run([sys.executable, "-m", "wordfreq", f], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
assert r.stdout.splitlines() == ["b 3", "a 2", "c 1"], f"COUNTEREXAMPLE: got {r.stdout.splitlines()!r}, want ['b 3', 'a 2', 'c 1']"
print("ok")
