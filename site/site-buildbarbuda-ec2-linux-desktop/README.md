If you run (and use your own three passwords) below:

 ```
 docker-compose down
 MYSQL_ROOT_PASSWORD=please..change..this.password MYSQL_PASSWORD=please.change..this..password WEB_ADMIN_PASSWORD=please.change..this..password docker-compose up -d
 docker-compose logs --follow
 ```

You will have:
* your new HTTPS website on port 443, which you can log in as user `admin` and the 3rd password you choose
* a MySQL database for Drupal available on port 3306, which you can log in as user `root` and the 1st password you choose, or the user `drupal` and the 2nd password you choose

If you want to get a Linux prompt to your website, do:

```
docker exec -it siteec2linuxdesktop_buildbarbuda_1 bash --login
```
