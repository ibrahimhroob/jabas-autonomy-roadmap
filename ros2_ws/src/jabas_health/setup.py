from setuptools import find_packages, setup

package_name = "jabas_health"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="JABAS AI Autonomy",
    maintainer_email="autonomy@jabas.ai",
    description="Autonomy health aggregation and data-engine event triggering (C9).",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "health_aggregator = jabas_health.health_aggregator:main",
            "event_trigger = jabas_health.event_trigger:main",
        ],
    },
)
