#!/bin/sh
# postinst script for meniscus
#
# see: dh_installdeb(1)

set -e

# summary of how this script can be called:
#        * <postinst> `configure' <most-recently-configured-version>
#        * <old-postinst> `abort-upgrade' <new version>
#        * <conflictor's-postinst> `abort-remove' `in-favour' <package>
#          <new-version>
#        * <postinst> `abort-remove'
#        * <deconfigured's-postinst> `abort-deconfigure' `in-favour'
#          <failed-install-package> <version> `removing'
#          <conflicting-package> <version>
# for details, see http://www.debian.org/doc/debian-policy/ or
# the debian-policy package


case "$1" in
    configure)
	    . /usr/share/debconf/confmodule

	    if ! (getent group meniscus) > /dev/null 2>&1; then
	        addgroup --quiet --system meniscus > /dev/null
		fi

		if ! (getent passwd meniscus) > /dev/null 2>&1; then
		    adduser --quiet --system --home /var/lib/meniscus --ingroup meniscus --no-create-home --shell /bin/false meniscus
		fi

		chmod 0755 /etc/init.d/meniscus

		if [ ! -d /var/log/meniscus ]; then
            mkdir /var/log/meniscus
            chown -R meniscus:adm /var/log/meniscus/
            chmod 0750 /var/log/meniscus/
        fi

        if [ ! -d /var/lib/meniscus ]; then
            mkdir /var/lib/meniscus
            chown meniscus:meniscus -R /var/lib/meniscus/ /etc/meniscus
            chmod -R 0700 /etc/meniscus/
        fi
    ;;

    abort-upgrade|abort-remove|abort-deconfigure)
    ;;

    *)
        echo "postinst called with unknown argument \`$1'" >&2
        exit 1
    ;;
esac

# dh_installdeb will replace this with shell code automatically
# generated by other debhelper scripts.

#DEBHELPER#

exit 0