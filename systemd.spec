Name:           systemd
Url:            http://www.freedesktop.org/wiki/Software/systemd
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Version:        10
Release:        2%{?dist}.1
License:        GPLv2+
Group:          System Environment/Base
Summary:        A System and Session Manager
BuildRequires:  libudev-devel >= 160
BuildRequires:  libcap-devel
BuildRequires:  tcp_wrappers-devel
BuildRequires:  pam-devel
BuildRequires:  libselinux-devel
BuildRequires:  audit-libs-devel
BuildRequires:  libxslt
BuildRequires:  docbook-style-xsl
BuildRequires:  dbus-glib-devel
BuildRequires:  vala >= 0.9
BuildRequires:  pkgconfig
BuildRequires:  gtk2-devel
BuildRequires:  automake
BuildRequires:  autoconf
BuildRequires:  libtool
Requires:       systemd-units = %{version}-%{release}
Requires:       dbus >= 1.3.2
Requires:       udev >= 160
Requires:       libudev >= 160
Requires:       initscripts >= 9.18
Requires:       selinux-policy >= 3.8.7
Requires:       kernel >= 2.6.35.2-9.fc14
Source0:        http://www.freedesktop.org/software/systemd/%{name}-%{version}.tar.bz2

%description
systemd is a system and session manager for Linux, compatible with
SysV and LSB init scripts. systemd provides aggressive parallelization
capabilities, uses socket and D-Bus activation for starting services,
offers on-demand starting of daemons, keeps track of processes using
Linux cgroups, supports snapshotting and restoring of the system
state, maintains mount and automount points and implements an
elaborate transactional dependency-based service control logic. It can
work as a drop-in replacement for sysvinit.

%package units
Group:          System Environment/Base
Summary:        Configuration files, directories and installation tool for systemd
Requires:       pkgconfig
Requires(post): coreutils
Requires(post): gawk

%description units
Basic configuration files, directories and installation tool for the systemd
system and session manager.

%package gtk
Group:          System Environment/Base
Summary:        Graphical frontend for systemd
Requires:       %{name} = %{version}-%{release}

%description gtk
Graphical front-end for systemd.

%package sysvinit
Group:          System Environment/Base
Summary:        systemd System V init tools
Requires:       %{name} = %{version}-%{release}
Obsoletes:      SysVinit < 2.86-24, sysvinit < 2.86-24
Provides:       SysVinit = 2.86-24, sysvinit = 2.86-24
Provides:       sysvinit-userspace
Obsoletes:      upstart < 0.6.5-6.fc14
Conflicts:      upstart-sysvinit

# For now, require upstart installed, so that people can rely that
# they can emergency boot into upstart with init=/sbin/upstart
Requires:       upstart >= 0.6.5-6.fc14

%description sysvinit
Drop-in replacement for the System V init tools of systemd.

%prep
%setup -q

%build
%configure --with-rootdir= --with-distro=fedora
make %{?_smp_mflags}

%install
rm -rf %{buildroot}
make DESTDIR=%{buildroot} install
find %{buildroot} \( -name '*.a' -o -name '*.la' \) -exec rm {} \;

# Create SysV compatibility symlinks. systemctl/systemd are smart
# enough to detect in which way they are called.
mkdir -p %{buildroot}/sbin
ln -s ../bin/systemd %{buildroot}/sbin/init
ln -s ../bin/systemctl %{buildroot}/sbin/reboot
ln -s ../bin/systemctl %{buildroot}/sbin/halt
ln -s ../bin/systemctl %{buildroot}/sbin/poweroff
ln -s ../bin/systemctl %{buildroot}/sbin/shutdown
ln -s ../bin/systemctl %{buildroot}/sbin/telinit
ln -s ../bin/systemctl %{buildroot}/sbin/runlevel

# We create all wants links manually at installation time to make sure
# they are not owned and hence overriden by rpm after the used deleted
# them.
rm -r %{buildroot}/etc/systemd/system/*.target.wants

# And the default symlink we generate automatically based on inittab
rm %{buildroot}/etc/systemd/system/default.target

# These are now in the initscripts package
rm -f %{buildroot}/lib/systemd/system/{halt,killall,poweroff,prefdm,rc-local,reboot,single,sysinit}.service
rm -f %{buildroot}/%{_sysconfdir}/rc.d/init.d/reboot
rm -f    %{buildroot}/%{_sysconfdir}/systemd/system/ctrl-alt-del.target \
   %{buildroot}/%{_sysconfdir}/systemd/system/display-manager.service \
   %{buildroot}/%{_sysconfdir}/systemd/system/kbrequest.target

sed -i -e 's/^#MountAuto=yes$/MountAuto=no/' \
        -e 's/^#SwapAuto=yes$/SwapAuto=no/' %{buildroot}/etc/systemd/system.conf

# Make sure the %ghost-ing below works
touch %{buildroot}%{_sysconfdir}/systemd/system/runlevel2.target
touch %{buildroot}%{_sysconfdir}/systemd/system/runlevel3.target
touch %{buildroot}%{_sysconfdir}/systemd/system/runlevel4.target
touch %{buildroot}%{_sysconfdir}/systemd/system/runlevel5.target

mkdir -p %{buildroot}%{_localstatedir}/run/user

# Make sure these directories are properly owned
mkdir -p %{buildroot}/lib/systemd/system/basic.target.wants
mkdir -p %{buildroot}/lib/systemd/system/default.target.wants
mkdir -p %{buildroot}/lib/systemd/system/dbus.target.wants
mkdir -p %{buildroot}/lib/systemd/system/syslog.target.wants

%clean
rm -rf $RPM_BUILD_ROOT

%post
/bin/systemctl daemon-reexec > /dev/null 2>&1 || :

%post units
if [ $1 -eq 1 ] ; then
        # Try to read default runlevel from the old inittab if it exists
        runlevel=$(/bin/awk -F ':' '$3 == "initdefault" && $1 !~ "^#" { print $2 }' /etc/inittab 2> /dev/null)
        if [ -z "$runlevel" ] ; then
                target="/lib/systemd/system/graphical.target"
        else
                target="/lib/systemd/system/runlevel$runlevel.target"
        fi

        # And symlink what we found to the new-style default.target
        /bin/ln -sf "$target" /etc/systemd/system/default.target > /dev/null 2>&1 || :

        # Enable the services we install by default.
        /bin/systemctl enable \
                getty@.service \
                getty.target \
                remote-fs.target > /dev/null 2>&1 || :

        # Temporary fix for broken upgrades between older F14 rawhide to newer F14 rawhide. Should be removed eventually.
        /bin/systemctl enable \
                dbus.service \
                dbus.socket > /dev/null 2>&1 || :
fi

%preun units
if [ $1 -eq 0 ] ; then
        /bin/systemctl disable \
                getty@.service \
                getty.target \
                remote-fs.target > /dev/null 2>&1 || :

        /bin/rm -f /etc/systemd/system/default.target > /dev/null 2>&1 || :
fi

%postun units
if [ $1 -ge 1 ] ; then
        /bin/systemctl daemon-reload > /dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/dbus-1/system.d/org.freedesktop.systemd1.conf
%dir %{_sysconfdir}/systemd/session
%{_sysconfdir}/xdg/systemd
/bin/systemd
/bin/systemd-notify
/lib/systemd/systemd-*
/lib/udev/rules.d/*.rules
/%{_lib}/security/pam_systemd.so
%{_bindir}/systemd-cgls
%{_mandir}/man1/systemd.*
%{_mandir}/man1/systemd-notify.*
%{_mandir}/man1/systemd-cgls.*
%{_mandir}/man3/*
%{_mandir}/man5/*
%{_mandir}/man7/*
%{_mandir}/man8/pam_systemd.*
%{_datadir}/systemd
%{_datadir}/dbus-1/services/org.freedesktop.systemd1.service
%{_datadir}/dbus-1/system-services/org.freedesktop.systemd1.service
%{_datadir}/dbus-1/interfaces/org.freedesktop.systemd1.*.xml
%{_docdir}/systemd
%dir %{_localstatedir}/run/user

%files units
%defattr(-,root,root,-)
%dir %{_sysconfdir}/systemd
%dir %{_sysconfdir}/systemd/system
%config(noreplace) %{_sysconfdir}/systemd/system.conf
%dir /lib/systemd
/lib/systemd/system
/bin/systemctl
%{_mandir}/man1/systemctl.*
%{_datadir}/pkgconfig/systemd.pc
%{_docdir}/systemd/LICENSE

# Make sure we don't remove runlevel targets from F14 alpha installs,
# but make sure we don't create then anew.
%ghost %config(noreplace) %{_sysconfdir}/systemd/system/runlevel2.target
%ghost %config(noreplace) %{_sysconfdir}/systemd/system/runlevel3.target
%ghost %config(noreplace) %{_sysconfdir}/systemd/system/runlevel4.target
%ghost %config(noreplace) %{_sysconfdir}/systemd/system/runlevel5.target

%files gtk
%defattr(-,root,root,-)
%{_bindir}/systemadm
%{_mandir}/man1/systemadm.*

%files sysvinit
%defattr(-,root,root,-)
/sbin/init
/sbin/reboot
/sbin/halt
/sbin/poweroff
/sbin/shutdown
/sbin/telinit
/sbin/runlevel
%{_mandir}/man1/init.*
%{_mandir}/man8/halt.*
%{_mandir}/man8/reboot.*
%{_mandir}/man8/shutdown.*
%{_mandir}/man8/poweroff.*
%{_mandir}/man8/telinit.*
%{_mandir}/man8/runlevel.*

%changelog
* Tue Oct 05 2010 jkeating - 10-2.1
- Rebuilt for gcc bug 634757

* Tue Sep 14 2010 Lennart Poettering <lpoetter@redhat.com> - 10-2
- Enable audit
- https://bugzilla.redhat.com/show_bug.cgi?id=633771

* Tue Sep 14 2010 Lennart Poettering <lpoetter@redhat.com> - 10-1
- New upstream release
- https://bugzilla.redhat.com/show_bug.cgi?id=630401
- https://bugzilla.redhat.com/show_bug.cgi?id=630225
- https://bugzilla.redhat.com/show_bug.cgi?id=626966
- https://bugzilla.redhat.com/show_bug.cgi?id=623456

* Fri Sep  3 2010 Bill Nottingham <notting@redhat.com> - 9-3
- move fedora-specific units to initscripts; require newer version thereof

* Fri Sep  3 2010 Lennart Poettering <lpoetter@redhat.com> - 9-2
- Add missing tarball

* Fri Sep  3 2010 Lennart Poettering <lpoetter@redhat.com> - 9-1
- New upstream version
- Closes 501720, 614619, 621290, 626443, 626477, 627014, 627785, 628913

* Fri Aug 27 2010 Lennart Poettering <lpoetter@redhat.com> - 8-3
- Reexecute after installation, take ownership of /var/run/user
- https://bugzilla.redhat.com/show_bug.cgi?id=627457
- https://bugzilla.redhat.com/show_bug.cgi?id=627634

* Thu Aug 26 2010 Lennart Poettering <lpoetter@redhat.com> - 8-2
- Properly create default.target link

* Wed Aug 25 2010 Lennart Poettering <lpoetter@redhat.com> - 8-1
- New upstream release

* Thu Aug 12 2010 Lennart Poettering <lpoetter@redhat.com> - 7-3
- Fix https://bugzilla.redhat.com/show_bug.cgi?id=623561

* Thu Aug 12 2010 Lennart Poettering <lpoetter@redhat.com> - 7-2
- Fix https://bugzilla.redhat.com/show_bug.cgi?id=623430

* Tue Aug 10 2010 Lennart Poettering <lpoetter@redhat.com> - 7-1
- New upstream release

* Fri Aug  6 2010 Lennart Poettering <lpoetter@redhat.com> - 6-2
- properly hide output on package installation
- pull in coreutils during package installtion

* Fri Aug  6 2010 Lennart Poettering <lpoetter@redhat.com> - 6-1
- New upstream release
- Fixes #621200

* Wed Aug  4 2010 Lennart Poettering <lpoetter@redhat.com> - 5-2
- Add tarball

* Wed Aug  4 2010 Lennart Poettering <lpoetter@redhat.com> - 5-1
- Prepare release 5

* Tue Jul 27 2010 Bill Nottingham <notting@redhat.com> - 4-4
- Add 'sysvinit-userspace' provide to -sysvinit package to fix upgrade/install (#618537)

* Sat Jul 24 2010 Lennart Poettering <lpoetter@redhat.com> - 4-3
- Add libselinux to build dependencies

* Sat Jul 24 2010 Lennart Poettering <lpoetter@redhat.com> - 4-2
- Use the right tarball

* Sat Jul 24 2010 Lennart Poettering <lpoetter@redhat.com> - 4-1
- New upstream release, and make default

* Tue Jul 13 2010 Lennart Poettering <lpoetter@redhat.com> - 3-3
- Used wrong tarball

* Tue Jul 13 2010 Lennart Poettering <lpoetter@redhat.com> - 3-2
- Own /cgroup jointly with libcgroup, since we don't dpend on it anymore

* Tue Jul 13 2010 Lennart Poettering <lpoetter@redhat.com> - 3-1
- New upstream release

* Fri Jul 9 2010 Lennart Poettering <lpoetter@redhat.com> - 2-0
- New upstream release

* Wed Jul 7 2010 Lennart Poettering <lpoetter@redhat.com> - 1-0
- First upstream release

* Tue Jun 29 2010 Lennart Poettering <lpoetter@redhat.com> - 0-0.7.20100629git4176e5
- New snapshot
- Split off -units package where other packages can depend on without pulling in the whole of systemd

* Tue Jun 22 2010 Lennart Poettering <lpoetter@redhat.com> - 0-0.6.20100622gita3723b
- Add missing libtool dependency.

* Tue Jun 22 2010 Lennart Poettering <lpoetter@redhat.com> - 0-0.5.20100622gita3723b
- Update snapshot

* Mon Jun 14 2010 Rahul Sundaram <sundaram@fedoraproject.org> - 0-0.4.20100614git393024
- Pull the latest snapshot that fixes a segfault. Resolves rhbz#603231

* Thu Jun 11 2010 Rahul Sundaram <sundaram@fedoraproject.org> - 0-0.3.20100610git2f198e
- More minor fixes as per review

* Thu Jun 10 2010 Rahul Sundaram <sundaram@fedoraproject.org> - 0-0.2.20100610git2f198e
- Spec improvements from David Hollis

* Wed Jun 09 2010 Rahul Sundaram <sundaram@fedoraproject.org> - 0-0.1.20090609git2f198e
- Address review comments

* Tue Jun 01 2010 Rahul Sundaram <sundaram@fedoraproject.org> - 0-0.0.git2010-06-02
- Initial spec (adopted from Kay Sievers)
