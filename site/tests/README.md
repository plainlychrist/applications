# Testing?

Just run `./run-tests.sh`

# Developing your own tests?

```bash
docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-bootstrap.yml up -d
docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-bootstrap.yml logs -f

# ... do your manual testing ... example: curl -kv https://localhost:10443
# ... create test code from what you did manually ...

docker-compose -p "plainlychristtests" -f setup/docker-compose-site-empty-bootstrap.yml down

# ... now you can try to run it automatically ...
./run-tests.sh
```
