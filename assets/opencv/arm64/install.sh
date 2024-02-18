set -e

cd /tmp/
wget --quiet https://assets.duckietown.com/python/wheels/opencv_python_headless-4.8.1.78-cp311-cp311-linux_aarch64.whl
python3 -m pip install ./opencv_python_headless-4.8.1.78-cp311-cp311-linux_aarch64.whl numpy==1.26.2
rm ./opencv_python_headless-4.8.1.78-cp311-cp311-linux_aarch64.whl
