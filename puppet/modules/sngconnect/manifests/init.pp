class sngconnect {
    include apt
    include apt::params

    exec { 'update-package-repositories':
        command   => "${apt::params::provider} update",
        logoutput => 'on_failure',
    }
    exec { 'update-packages':
        command   => "${apt::params::provider} -y dist-upgrade",
        logoutput => 'on_failure',
        require   => Exec['update-package-repositories'],
    }
    Exec['update-packages'] -> Package <| |>
    Exec['update-packages'] -> Apt::Source <| |>
    Exec['update-packages'] -> Apt::Key <| |>

    class command-line-utils {
        package { 'build-essential':
            ensure => present,
        }
        package { 'binutils':
            ensure => present,
        }
        package { 'gfortran':
            ensure => present,
        }
        package { 'ack-grep':
            ensure => present,
        }
        package { 'htop':
            ensure => present,
        }
        package { 'telnet':
            ensure => present,
        }
        package { 'curl':
            ensure => present,
        }
        package { 'netcat':
            ensure => present,
        }
        package { 'bash-completion':
            ensure => present,
        }
        package { 'git':
            ensure => present,
        }
        package { 'vim-nox':
            ensure => present,
        }
    }

    class python {
        package { 'python':
            ensure => present,
        }
        package { 'python-dev':
            ensure => present,
        }
        package { 'python-virtualenv':
            ensure => present,
        }
    }

    class postgresql {
        include postgresql
        include postgresql::server
        package { 'postgresql-server-dev-all':
            ensure => present,
        }
        postgresql::db { 'sngconnect':
            user     => 'sngconnect',
            password => 'sngconnect',
        }
    }

    class cassandra {
        apt::source { 'apache-cassandra':
            location    => 'http://www.apache.org/dist/cassandra/debian',
            release     => '11x',
            repos       => 'main',
            key         => 'F758CE318D77295D',
            key_server  => 'pgp.mit.edu',
            include_src => 'true',
        }
        apt::key { 'apache-cassandra-0.7.5-key':
            key        => '2B5C1B00',
            key_server => 'pgp.mit.edu',
        }
        exec { 'update-cassandra-repository':
            command   => "${apt::params::provider} update",
            logoutput => 'on_failure',
            require => [
                Apt::Source['apache-cassandra'],
                Apt::Key['apache-cassandra-0.7.5-key'],
            ],
        }
        package { 'cassandra':
            ensure  => present,
            require => [
                Exec['update-cassandra-repository'],
            ],
        }
        service { 'cassandra':
            name    => 'cassandra',
            ensure  => running,
            require => Package['cassandra'],
        }
    }

    class virtualenv {
        exec { 'create-virtualenv':
            command   => '/usr/bin/virtualenv /home/vagrant/environment',
            creates   => '/home/vagrant/environment',
            user      => 'vagrant',
            logoutput => 'on_failure',
            require   => Class['python'],
        }
        exec { 'install-numpy':
            command   => '. /home/vagrant/environment/bin/activate && pip install numpy',
            provider  => shell,
            user      => 'vagrant',
            logoutput => 'on_failure',
            require   => [
                Exec['create-virtualenv'],
                Class['command-line-utils'],
            ],
        }
        exec { 'install-application':
            command   => '. /home/vagrant/environment/bin/activate && cd /vagrant && python setup.py develop',
            provider  => shell,
            user      => 'vagrant',
            logoutput => 'on_failure',
            require   => [
                Exec['install-numpy'],
                Class['postgresql'],
                Class['command-line-utils'],
            ],
        }
    }

    class setup-application {
        exec { 'initialize-database':
            command   => '. /home/vagrant/environment/bin/activate && /home/vagrant/environment/bin/sng_initialize_database /vagrant/development.ini',
            provider  => shell,
            user      => 'vagrant',
            logoutput => 'on_failure',
            require   => [
                Class['virtualenv'],
                Class['postgresql'],
            ],
        }
        exec { 'initialize-cassandra':
            command   => '. /home/vagrant/environment/bin/activate && /home/vagrant/environment/bin/sng_initialize_cassandra /vagrant/development.ini',
            provider  => shell,
            user      => 'vagrant',
            logoutput => 'on_failure',
            require   => [
                Class['virtualenv'],
                Class['cassandra'],
            ],
        }
        file { '/home/vagrant/var':
            owner  => 'vagrant',
            ensure => 'directory',
        }
        file { '/home/vagrant/var/log':
            owner  => 'vagrant',
            ensure => 'directory',
            require => File['/home/vagrant/var'],
        }
        file { '/home/vagrant/var/run':
            owner  => 'vagrant',
            ensure => 'directory',
            require => File['/home/vagrant/var'],
        }
        file { '/home/vagrant/sngconnect':
            mode    => 0754,
            owner   => 'vagrant',
            content => template('sngconnect/sngconnect.erb'),
        }
        service { 'sngconnect':
            name => 'pserve',
            path => '/home/vagrant',
            provider => init,
            start => '/home/vagrant/sngconnect start',
            restart => '/home/vagrant/sngconnect restart',
            stop => '/home/vagrant/sngconnect stop',
            status => '/home/vagrant/sngconnect status',
            ensure => running,
            require => [
                Class['virtualenv'],
                Exec['initialize-database'],
                Exec['initialize-cassandra'],
                File['/home/vagrant/var/run'],
                File['/home/vagrant/var/log'],
                File['/home/vagrant/sngconnect'],
            ]
        }
    }

    include command-line-utils
    include python
    include postgresql
    include cassandra
    include virtualenv
    include setup-application
}
