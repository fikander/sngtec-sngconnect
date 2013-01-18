from fabric import api as fabric

fabric.env.use_ssh_config = True
fabric.env.hosts = [
    'server.synergiatech.pl',
]

@fabric.task
def update_code():
    with fabric.cd('~/sngconnect'):
        fabric.run('git pull')

@fabric.task
def stop_application_server():
    fabric.run('./stop_server.sh')

@fabric.task
def clean_installation():
    with fabric.cd('~/environment'):
        fabric.run('rm -r lib/python2.6/site-packages/sngconnect-0.0-py2.6.egg')
        fabric.run('find . -name \'*.pyc\' -delete')
    with fabric.cd('~/sngconnect'):
        fabric.run('find . -name \'*.pyc\' -delete')

@fabric.task
def clean_application_log():
    fabric.run('rm var/log/pserve.log')

@fabric.task
def install_application():
    with fabric.cd('~/sngconnect'):
        fabric.run('. ../environment/bin/activate && python setup.py install')

@fabric.task
def start_application_server():
    fabric.run('./start_server.sh')

@fabric.task
def deploy():
    fabric.execute(update_code)
    fabric.execute(stop_application_server)
    fabric.execute(clean_installation)
    fabric.execute(clean_application_log)
    fabric.execute(install_application)
    fabric.execute(start_application_server)
