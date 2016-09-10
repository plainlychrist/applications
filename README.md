# applications
Definitions for how to run the applications, like the website application

# Layout

site/
: All definitions for running the website application

site/site-ec2-linux-desktop/
: The definition for running the website application on an EC2 development desktop

site/site-normal-linux-desktop/
: The definition for running the website application on a normal linux desktop

# Running

```bash
cd site/site-normal-linux-desktop
MYSQL_ROOT_PASSWORD=make-some-password MYSQL_PASSWORD=make-another-password WEB_ADMIN_PASSWORD=you-need-to-remember-this-password docker-compose up
docker-compose rm
```
