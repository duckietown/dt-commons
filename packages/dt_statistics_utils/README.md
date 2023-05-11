# Statistics collection


## Device statistics

You can use the module `dt_statistics_utils.device` to collect statistics about a device (i.e., robot).

We only support the creation of **Event** statistics through this library.
**Event** statistics are useful when we need to capture events of interest, for example, 
an update is downloaded, a hardware test is run, etc.


### Example

Use the following snippet to collect stats about the event `hardware/test/left-wheel-encoder` 
with payload `{"success": False, "reason": "Tick count does not change when I turn the wheel"}`.

```python
from dt_statistics_utils.device import log_event

log_event(
    "hardware/test/left-wheel-encoder", 
    data={
        "success": False, 
        "reason": "Tick count does not change when I turn the wheel"
    }
)
```
