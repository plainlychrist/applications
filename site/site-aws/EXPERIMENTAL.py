The `conf.py` is a script that will interactively let you deploy using CloudFormation.

It is experimental.

# How stacks are organized

We use the layered architecture described in [AWS CloudFormation Best Practices](http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html#organizingstacks).
This simplifies upgrading the site.

# Configuring

```
./conf.py network
./conf.py database
./conf.py compute
```

# PuTTY notes

You may have to run it with:

```
env - TERM=linux ./conf.py network
```

to get the console working correctly.
