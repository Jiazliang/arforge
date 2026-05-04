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
- default-driven package emission for base types, implementation data types, units, compu methods, and system output

Files to inspect:

- [company_layout.yaml](/d:/dev/arforge/examples/features/package_layout/packages/company_layout.yaml) defines allowed packages and category defaults
- [BrakeController.yaml](/d:/dev/arforge/examples/features/package_layout/swcs/BrakeController.yaml) assigns an SWC explicitly to `Components/Brake`
- [If_BrakeTorque.yaml](/d:/dev/arforge/examples/features/package_layout/interfaces/If_BrakeTorque.yaml) assigns an interface explicitly to `Interfaces/Brake`
- [application_types.yaml](/d:/dev/arforge/examples/features/package_layout/types/application_types.yaml) assigns an application data type explicitly to `DataTypes/Application`
- [brake_mode.yaml](/d:/dev/arforge/examples/features/package_layout/modes/brake_mode.yaml) assigns a mode declaration group explicitly to `Modes`

The remaining packageable elements in the example rely on category defaults from the external layout file, which is why the generated ARXML also contains packages such as `DataTypes/Base`, `DataTypes/Implementation`, `DataTypes/CompuMethods`, `DataTypes/Units`, and `System`.
