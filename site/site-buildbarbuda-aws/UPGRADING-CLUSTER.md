Your workflow is typically:

1. Build your changes to a development branch of `site-buildbarbuda`
2. Stop **one** of your ECS tasks, and wait for a new one to start. *Each time you stop an ECS task, the ECS service will start a new one; just give it some time until it is RUNNING*
    * If you were to log into any of your EC2 machines, and `docker ps` followed by `docker logs ecs-pc-...-EcsSiteTaskDef-...-site-buildbarbuda-...`, you would see a log message:
        Could not create the table site_phase1. Another creator on a machine was elected to create the Drupal tables.
    * That means the Drupal software and configuration is updated locally, but it hasn't applied the database changes yet because the table 'site_phase1' exists.
3. Log into the website, and go to https://your_development_site/admin/config/development/performance, and `Clear all caches`
4. Stop all the remaining ECS tasks, one at a time. Make sure all old ECS tasks are gone, and only new ECS tasks.
5. After your entire development cluster is running the new Drupal software and configuration, you should check the development site to see if there are any problems. *If you have a tool to check links, go ahead and do that.*
6. Upgrade the database by going to [your development site administrative update page](https://your_development_site/update.php)
7. Log into one of your EC2 machines, and do a `docker ps` followed by `docker exec -it ecs-pc-...-EcsSiteTaskDef-...-site-buildbarbuda-... bash -l`. Then run:
    ```
    ~drupaladmin/bin/drush sql-query 'DROP TABLE site_phase2' ; ~drupaladmin/bin/drush sql-query 'DROP TABLE site_phase1'
    ```
8. Stop **one** of your ECS tasks, and any remaining database updates (if any) will be applied automatically.
