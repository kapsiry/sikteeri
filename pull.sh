#!/bin/sh

# set up remotes
remote () {
	git remote show $1 >/dev/null 2>&1 && return # skip existing
	git remote add -t master -m master $@
}
remote hukka http://koti.kapsi.fi/hukka/django-sikteeri.git
remote gua https://gua.kapsi.fi/git/django-sikteeri.git
remote jkj http://koti.kapsi.fi/oh8glv/django-sikteeri.git
remote joneskoo http://joneskoo.kapsi.fi/django-sikteeri.git
remote ilkka http://koti.kapsi.fi/ilkka/django-sikteeri.git

git pull hukka master
git pull gua master
git pull jkj master
git pull joneskoo master
git pull ilkka master

