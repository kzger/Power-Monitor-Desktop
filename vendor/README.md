# vendor

Place the real `LibreHardwareMonitorLib.dll` file in this directory:

```text
vendor/LibreHardwareMonitorLib.dll
```

Download it from the official LibreHardwareMonitor GitHub releases or build
`LibreHardwareMonitorLib` from source.

For the release ZIP, keep the companion `*.dll` files in this directory too.
`LibreHardwareMonitorLib.dll` may need assemblies such as `System.Memory.dll`,
`HidSharp.dll`, and hardware toolkit DLLs at runtime.
