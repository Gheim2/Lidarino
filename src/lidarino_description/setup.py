import os
from glob import glob
from setuptools import setup

package_name = 'lidarino_description'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Copia i file Xacro e URDF
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro') + glob('urdf/*.urdf')),
        # Copia le mesh STL
        (os.path.join('share', package_name, 'urdf', 'meshes'), glob('urdf/meshes/*.stl')),
        # Copia i file di launch
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        # Copia i file di configurazione
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Giuseppe',
    maintainer_email='giuseppe@todo.todo',
    description='Pacchetto URDF e Mesh per Lidarino',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tof_merger = lidarino_description.tof_merger:main'
        ],
    },
)