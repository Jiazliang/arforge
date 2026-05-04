# ARForge: External package layout example

This example shows how to keep ARXML package layout outside the project file and assign selected packageable elements to explicit packages.

Key points:

- AUTOSAR packages are containers and namespaces for packageable elements.
- Package layout controls exported ARXML paths and namespaces only.
- Package layout does not create connectors, instances, or runtime behavior.
- Elements without an explicit `package` use the category default from the external layout file.

This fixture demonstrates:

- `autosar.packageLayoutRef` in [autosar.project.yaml](/d:/dev/arforge/examples/features/package_layout/autosar.project.yaml)
- explicit package assignment for an SWC, interface, application data type, and mode declaration group
- fallback to category defaults for unassigned SWCs and interfaces
- nested package paths such as `Components/Brake` and `DataTypes/Application`
