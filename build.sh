if test -e .git; then
    git-buildpackage --git-ignore-new -us -uc
else
    debuild -us -uc
fi
