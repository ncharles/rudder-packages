#####################################################################################
# Copyright 2011 Normation SAS
#####################################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, Version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#####################################################################################

#=================================================
# Variables
#=================================================
%define real_name               rudder-webapp
%define real_epoch              1398866025

%define rudderdir               /opt/rudder
%define ruddervardir            /var/rudder
%define rudderlogdir            /var/log/rudder
%define sharedir                /usr/share
%define bindir                  /usr/bin


%define config_repository_group rudder

%define maven_settings settings-external.xml

# Reference for suse_version : https://en.opensuse.org/openSUSE:Build_Service_cross_distribution_howto
%if 0%{?suse_version}
%define apache                  apache2
%define apache_tools            apache2-utils
%define apache_group            www
%define htpasswd_cmd            htpasswd2
%define ldap_clients            openldap2-client
%define jetty_init_script       jetty-sles.sh
%endif
%if 0%{?rhel}
%define apache                  httpd
%define apache_tools            httpd-tools
%define apache_group            apache
%define htpasswd_cmd            htpasswd
%define ldap_clients            openldap-clients
%define jetty_init_script       jetty-rpm.sh
%endif
%define apache_vhost_dir        %{apache}/vhosts.d

# avoid error during byte compilation of pyc since they are removed anyway
%define _python_bytecompile_errors_terminate_build 0


#=================================================
# Header
#=================================================
Summary: Configuration management and audit tool - webapp
Name: %{real_name}
Version: %{real_version}
Release: 1%{?dist}
Epoch: %{real_epoch}
License: GPLv3
URL: http://www.rudder-project.org

Group: Applications/System

Source1: rudder-users.xml
Source2: rudder.xml
Source5: rudder-upgrade
Source7: rudder-webapp
Source8: rudder-web
Source10: rudder-init
Source11: rudder-node-to-relay
Source12: rudder-root-rename
Source13: rudder-passwords.conf
Source14: rudder-plugin
Source15: post.write_technique.10_commit.sh
Source16: post.write_technique.50_rudderify.sh
Source17: rudder-metrics-reporting
Source18: ca-bundle.crt
Source19: rudder-reload-cf-serverd
Source20: rudder-webapp.te
Source22: rudder-keys
Source23: .gitignore
Source24: rudder-webapp-apache
Source25: rudder-apache-webapp-common.conf
Source26: rudder-apache-webapp-ssl.conf
Source27: rudder-apache-webapp-nossl.conf
Source28: rudder-webapp.fc
Source29: rudder-fix-repository-permissions
Source31: ncf_api_flask_app.wsgi
Source32: ncf-api-virtualenv.conf
Source33: ncf-api-virtualenv.te
Source34: ncf-api-virtualenv.fc
Source35: inventory-web.properties
Source36: rudder-inventory-endpoint-upgrade
Source37: rudder-inventory-endpoint
Source38: endpoint.xml
Source39: rudder-jetty.default
Source40: rudder-jetty.conf
Source41: rudder-jetty


BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

# Disable dependency auto-generation, to prevent Python requirements
# autodetection, which is not desired here.
AutoReq: 0
AutoProv: 0

# Add Requires here - order is important
BuildRequires: python
Requires: python

# Smooth upgrade
Obsoletes: ncf, ncf-api-virtualenv, rudder-techniques
# Prevent reinstalling old versions
Conflicts: ncf, ncf-api-virtualenv, rudder-techniques

# Dependencies
Requires: rudder-inventory-ldap = %{real_epoch}:%{real_version}, rudder-server-relay = %{real_epoch}:%{real_version}, %{apache}, %{apache_tools}, git-core, rsync, openssl, %{ldap_clients}

# We need the PostgreSQL client utilities so that we can run database checks and upgrades (rudder-upgrade, in particular)
Requires: postgresql >= 9.2

# TODO obsolete / provides / conflicts

# Use our own dependency generator to remove perl specific dependencies
%global _use_internal_dependency_generator 0
%global __find_requires_orig %{__find_requires}
%define __find_requires %{_sourcedir}/filter-reqs.pl true %{__find_requires_orig}
%global __find_provides_orig %{__find_provides}
%define __find_provides %{_sourcedir}/filter-reqs.pl true %{__find_provides_orig}

# OS-specific dependencies

##
## Those jetty packages are virtual packages provided by our Jetty and the system one.
##

## RHEL
%if 0%{?rhel}
BuildRequires: java-1.8.0-openjdk-devel selinux-policy-devel
# We need mod_wsgi to use ncf builder
Requires: mod_ssl httpd mod_wsgi shadow-utils
Requires: jre-headless >= 1.8
%endif

## SLES
%if 0%{?suse_version}
BuildRequires: jdk >= 1.8
Requires: apache2 apache2-mod_wsgi pwdutils python-pyOpenSSL
%endif

%if 0%{?sle_version} && 0%{?sle_version} >= 150000
Requires: java-10-openjdk-headless insserv-compat
%endif

%description
Rudder is an open source configuration management and audit solution.

This package contains the web application that is the main user interface to
Rudder. The webapp is automatically installed and started using the Jetty
application server bundled in the rudder-jetty package.

#=================================================
# Building
#=================================================
%build

cd %{_sourcedir}
make build

%if 0%{?rhel}
# Build SELinux policy package
# Compiles rudder-webapp.te and rudder-webapp.fc into rudder-webapp.pp
make -f /usr/share/selinux/devel/Makefile
%endif


#=================================================
# Installation
#=================================================
%install
rm -rf %{buildroot}

cd %{_sourcedir}
make install APACHE_VHOSTDIR=%{apache_vhost_dir} DESTDIR=%{buildroot}

%if 0%{?rhel}
  # Install SELinux policy
  install -m 644  ncf-api-virtualenv.pp %{buildroot}/usr/share/ncf-api-virtualenv/share/selinux/
  install -m 644  rudder-webapp.pp %{buildroot}%{rudderdir}/share/selinux/
  # Replace init script
  cp jetty/bin/jetty-rpm.sh jetty/bin/jetty.sh
%else
  # Replace init script
  cp jetty/bin/jetty-sles.sh jetty/bin/jetty.sh
%endif


#=================================================
# Pre Installation
#=================================================
%pre -n rudder-webapp

mkdir -p /opt/rudder/etc
echo 'root' > /opt/rudder/etc/uuid.hive

service rudder-jetty stop
if [ -x /opt/rudder/bin/rudder-pkg ]
then
  /opt/rudder/bin/rudder-pkg plugin save-status > /tmp/rudder-plugins-upgrade
fi

CFRUDDER_FIRST_INSTALL=$1

if [ ${CFRUDDER_FIRST_INSTALL} -ne 1 ]
then
    service rudder-jetty stop
fi

#=================================================
# Post Installation
#=================================================
%post -n rudder-webapp

RUDDER_FIRST_INSTALL="false"

if [ $1 -eq 1 ]
then
  RUDDER_FIRST_INSTALL="true"
fi

# Do this ONLY at first install
if [ $1 -eq 1 ]
then
  echo 'DAVLockDB /tmp/davlock.db' > /etc/%{apache}/conf.d/dav_mod.conf
fi

%if 0%{?suse_version}
a2enmod rewrite dav dav_fs ssl version wsgi

# Add required includes in the apache2 configuration
nextline=$(grep -A1 -E "^. /etc/sysconfig/rudder-relay-apache$" /etc/sysconfig/apache2 | tail -n1)
if [ "${nextline}" = "" ]; then
  # No include currently
  echo -e '# This sources the modules/defines needed by Rudder\n. /etc/sysconfig/rudder-relay-apache' >> /etc/sysconfig/apache2
  echo -e '# This line is necessary for fillup not to remove any lines above. See #11153\nAPACHE_RUDDER_RELAY_CUSTOMIZED="true"' >> /etc/sysconfig/apache2
fi
%endif


# Update /etc/sysconfig/apache2 in case an old module loading entry has already been created by Rudder
if [ -f /etc/sysconfig/apache2 ] && grep -q 'APACHE_MODULES="${APACHE_MODULES} rewrite dav dav_fs proxy proxy_http' /etc/sysconfig/apache2
then
  echo "INFO: Upgrading the /etc/sysconfig/apache2 file, Rudder needed modules for Apache are now listed in /etc/sysconfig/rudder-relay-apache"
  sed -i 's%APACHE_MODULES="${APACHE_MODULES} rewrite dav dav_fs proxy proxy_http.*%# This sources the Rudder needed by Rudder\n. /etc/sysconfig/rudder-relay-apache%' /etc/sysconfig/apache2
fi

%if 0%{?rhel}
# SELinux support
# Check "sestatus" presence, and if here tweak our installation to be
# SELinux compliant
if type sestatus >/dev/null 2>&1 && sestatus | grep -q "enabled"; then
  echo -n "INFO: Applying selinux policy..."
  # Add/Update the rudder-webapp SELinux policy
  semodule -i /opt/rudder/share/selinux/rudder-webapp.pp
  # Ensure inventory directories context is set by resetting
  # their context to the contexts defined in SELinux configuration,
  # including the file contexts defined in the rudder-webapp module
  restorecon -RF /var/rudder/configuration-repository/techniques

  # Add/Update the ncf-api-virtualenv SELinux policy
  semodule -i /usr/share/ncf-api-virtualenv/share/selinux/ncf-api-virtualenv.pp
  restorecon -RF /var/lib/ncf-api-venv/
  echo " Done"
fi
%endif

/opt/rudder/share/package-scripts/rudder-webapp-postinst "${FIRST_INSTALL}" "%{apache}" "%{apache_user}" "%{apache_group}"

#=================================================
# Post Uninstallation
#=================================================
%postun -n rudder-webapp

# Do it only during uninstallation
if [ $1 -eq 0 ]; then
  if getent group %{config_repository_group} > /dev/null; then
    # Remove the configuration-repository group
    echo -n "INFO: Removing group %{config_repository_group}..."
    groupdel %{config_repository_group}
    echo " Done"
  fi

%if 0%{?suse_version}
  # Remove required includes in the SLES apache2 configuration
  if [ -f /etc/sysconfig/apache2 ]; then
    sed -i "/# This sources the modules\/defines needed by Rudder/d" /etc/sysconfig/apache2
    sed -i "/. \/etc\/sysconfig\/rudder-webapp-apache/d" /etc/sysconfig/apache2

    # Also remove an older comment that was erroneously added until 2.11.21 / 3.0.16 / 3.1.10 / 3.2.3
    sed -i "/# This sources the configuration file needed by Rudder/d" /etc/sysconfig/apache2
  fi
%endif

fi

%if 0%{?rhel}
  # Do it only during uninstallation
  if [ $1 -eq 0 ]; then
    if type sestatus >/dev/null 2>&1 && sestatus | grep -q "enabled"; then
      if semodule -l | grep -q rudder-webapp; then
        echo -n "INFO: Removing selinux policy..."
        # Remove the ncf-api-virtualenv SELinux policy
        semodule -r ncf-api-virtualenv 2>/dev/null
        restorecon -RF /var/lib/ncf-api-venv/
        # Remove the rudder-webapp SELinux policy
        semodule -r rudder-webapp
        restorecon -RF /var/rudder/configuration-repository/techniques
        echo " Done"
      fi
    fi
  fi
%endif

# Do it only during uninstallation
if [ $1 -eq 0 ]; then
  # restart apache2 since it uses the user ncf
  systemctl restart %{apache} >/dev/null
  # Remove the package user
  if getent passwd ncf-api-venv >/dev/null; then
    echo -n "INFO: Removing the ncf-api-venv user..."
    userdel ncf-api-venv >/dev/null 2>&1
    echo " Done"
  fi
fi


#=================================================
# Pre Un-installation
#=================================================
%preun -n rudder-jetty

if [[ $1 -eq 0 ]]
then
  systemctl stop rudder-jetty
fi


#=================================================
# Cleaning
#=================================================
%clean
rm -rf %{buildroot}

#=================================================
# Files
#=================================================
%files -n rudder-webapp
%defattr(-, root, root, 0755)

%{rudderdir}/etc/
%config(noreplace) %{rudderdir}/etc/rudder-web.properties
%config(noreplace) %{rudderdir}/etc/rudder-users.xml
%config(noreplace) %{rudderdir}/etc/logback.xml
%config(noreplace) %{rudderdir}/etc/rudder-passwords.conf
%attr(0600, root, root) %{rudderdir}/etc/rudder-passwords.conf

/opt/rudder/jetty
/opt/rudder/etc/rudder-jetty-base
%{rudderlogdir}/webapp
/var/rudder/run
/opt/rudder/bin/rudder-jetty.sh
%config(noreplace) /etc/default/rudder-jetty
/opt/rudder/etc/rudder-jetty.conf
/usr/lib/systemd/system/

%{rudderdir}/bin/
%{rudderdir}/bin/rudder-node-to-relay
%{rudderdir}/bin/rudder-init
%{rudderdir}/bin/rudder-init.sh
%{rudderdir}/bin/rudder-root-rename
%{rudderdir}/bin/rudder-reload-cf-serverd
%{rudderdir}/share/techniques/
%{rudderdir}/share/tools/
%{rudderdir}/share/webapps/
%{rudderdir}/share/rudder-plugins/
%{rudderdir}/share
%{ruddervardir}/inventories/received
%{ruddervardir}/inventories/failed
%{ruddervardir}/configuration-repository/.gitignore
%{ruddervardir}/configuration-repository/ncf/ncf-hooks.d
%{rudderlogdir}/apache2/
/etc/%{apache_vhost_dir}/
%config %{rudderdir}/etc/rudder-apache-webapp-common.conf
%config %{rudderdir}/etc/rudder-apache-webapp-ssl.conf
%config %{rudderdir}/etc/rudder-apache-webapp-nossl.conf
%config(noreplace) /etc/sysconfig/rudder-webapp-apache
/usr/share/doc/rudder
%{sharedir}/ncf/
%config(noreplace) %{sharedir}/ncf/tree/ncf.conf
%{bindir}/ncf
/usr/share/ncf-api-virtualenv/
%attr(- , ncf-api-venv,ncf-api-venv) /var/lib/ncf-api-venv/
%{apache_vhost_dir}/ncf-api-virtualenv.conf

%config(noreplace) /opt/rudder/etc/inventory-web.properties


%if ! 0%{?suse_version}
# Avoid having .pyo and .pyc files in our package
# as they will always be regenerated
%exclude %{sharedir}/ncf/tree/10_ncf_internals/modules/templates/*.pyc
%exclude %{sharedir}/ncf/tree/10_ncf_internals/modules/templates/*.pyo
%endif


#=================================================
# Changelog
#=================================================
%changelog
* Wed Nov  22 2017 - Rudder Team <rudder-dev@rudder-project.org> %{version}
- See https://www.rudder-project.org/site/documentation/user-manual/ for changelogs
