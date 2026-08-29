import subprocess, sys, tempfile, os
r = subprocess.run([sys.executable, "-m", "wordfreq", "/nonexistent/nope.txt"], capture_output=True, text=True)
assert r.returncode == 2, f"COUNTEREXAMPLE: missing file exit {r.returncode}, want 2"
assert r.stderr.startswith("error:"), f"COUNTEREXAMPLE: stderr {r.stderr!r}"
assert r.stdout == ""
d = tempfile.mkdtemp(); f = os.path.join(d, "e.txt"); open(f, "w").write("")
r = subprocess.run([sys.executable, "-m", "wordfreq", f], capture_output=True, text=True)
assert r.returncode == 0 and r.stdout == "", "COUNTEREXAMPLE: empty file must print nothing and exit 0"
print("ok")
