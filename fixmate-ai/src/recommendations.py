"""Safe, non-destructive recommendations for detected system issues."""

CPU_HIGH_EXPLANATION = (
    "CPU usage is above 90%, which can make applications slow or unresponsive."
)
CPU_HIGH_RECOMMENDATION = (
    "Review the top processes and close only applications you recognize and no longer need."
)

MEMORY_HIGH_EXPLANATION = (
    "Memory usage is above 85%, leaving limited room for applications and the operating system."
)
MEMORY_HIGH_RECOMMENDATION = (
    "Save your work, close unused applications, and restart the computer if usage stays high."
)

DISK_LOW_EXPLANATION = (
    "Less than 10% of the system disk is free, which can affect updates and application stability."
)
DISK_LOW_RECOMMENDATION = (
    "Remove unneeded files with the operating system's storage tools or move personal files to another drive."
)

