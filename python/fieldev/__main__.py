'''
python -m fieldev run APP [--name value ...]    run a FielDev app without a window (the same as `FielDev run ...`)
python -m fieldev export SCRIPT [-o FILE]       bundle a script into an app
python -m fieldev info APP                      what an app asks for

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import sys

from fieldev import app_package

if __name__ == '__main__':
    sys.exit(app_package.main(sys.argv[1:]))
