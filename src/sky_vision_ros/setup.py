# ~/sky_vision/src/sky_vision_ros/setup.py
from setuptools import setup

package_name = 'sky_vision_ros'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sky_vision',
    maintainer_email='your.email@example.com',
    description='Sky Vision generic drone tracking, inspection, and picking ROS 2 nodes',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Flight Control
            'offboard_control = sky_vision_ros.offboard_control_node:main',
            # Vision
            'vision_tracker    = sky_vision_ros.vision_tracker_node:main',
            # Video Streaming
            'video_streamer     = sky_vision_ros.video_streamer_node:main',
            'video_streamer_qgc = sky_vision_ros.qgc_video_streamer_node:main',
            # Database
            'database_logger   = sky_vision_ros.database_logger_node:main',
            # Picking
            'picking_manager   = sky_vision_ros.picking_manager_node:main',
        ],
    },

    # =========================================================
    # Build & run after any edit:
    # cd ~/sky_vision
    # colcon build --packages-select sky_vision_ros --symlink-install
    #
    # Make nodes executable:
    # chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/*_node.py
    # =========================================================
)
