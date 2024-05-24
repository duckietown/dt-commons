set -e

cd /tmp/
wget --quiet https://assets.duckietown.com/python/wheels/opencv_python_headless-4.9.0.80-cp312-cp312-linux_aarch64.whl
python3 -m pip install ./opencv_python_headless-4.9.0.80-cp312-cp312-linux_aarch64.whl numpy==1.26.4
rm ./opencv_python_headless-4.9.0.80-cp312-cp312-linux_aarch64.whl
