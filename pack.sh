#!/bin/bash

cd zqcms
git pull -f
cd ..
python pack.py
echo "=== sync files to cdn"
./qrsync zqcms_update.json
echo "=== files sync done"
source config
./qboxrsctl login $USERNAME $PADDWORD
echo "=== refresh cdn caches"
./qboxrsctl refresh update
./qboxrsctl cdn/refresh $CDN_PATH/verinfo.txt
./qboxrsctl cdn/refresh $CDN_PATH/latest.zip
ZQCMS_VERSIONS=$(cat dist/source/caches/update/ver.txt)
if [ -n "$ZQCMS_VERSIONS" ]; then
    cat "dist/$ZQCMS_VERSIONS.file.txt" | while read line
    do
        ./qboxrsctl cdn/refresh $CDN_PATH/$line
    done
else
    echo "!!!=== ZQCMS_VERSIONS is null"
fi
echo "=== All done!"