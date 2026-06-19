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

NO_ACTIVE_INTERFACE_EXPLANATION = (
    "The computer has no active network interface with a usable IP address."
)
NO_ACTIVE_INTERFACE_RECOMMENDATION = (
    "Check that Wi-Fi or Ethernet is enabled and connected, then use your operating system's network status screen."
)

NO_INTERNET_EXPLANATION = (
    "A local network interface is active, but the configured internet test could not connect."
)
NO_INTERNET_RECOMMENDATION = (
    "Check another trusted website or device, then restart your router only if it is safe and you manage that equipment."
)

NETWORK_TIMEOUT_EXPLANATION = (
    "The connectivity test exceeded its short timeout, which may indicate a slow or filtered connection."
)
NETWORK_TIMEOUT_RECOMMENDATION = (
    "Retry the diagnostic and check the router or service status; do not disable firewall or security software."
)

HIGH_LATENCY_EXPLANATION = (
    "The connection succeeded, but its response time was above the configured threshold."
)
HIGH_LATENCY_RECOMMENDATION = (
    "Pause bandwidth-heavy applications you recognize, move closer to Wi-Fi, or compare with a wired connection."
)

