# Testing?

Just run `./run-tests.sh`

# Developing your own tests?

```bash
docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-a-bootstrap.yml up -d
docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-a-bootstrap.yml logs -f

# ... do your manual testing ... example: curl -kv https://localhost:10443
# ... create test code from what you did manually ...

docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-a-bootstrap.yml down

# ... now you can try to run it automatically ...
./run-tests.sh
```

# Debugging tests

Full instructions are at [pytest's Dropping to PDB (Python Debugger) on failures](http://docs.pytest.org/en/latest/usage.html#dropping-to-pdb-python-debugger-on-failures)

Basically:
1. Add `import pytest` to the imports at the top of your test module
2. Add `pytest.set_trace()` to where you want to set a breakpoint
3. Run `./run-tests.sh --pdb`
