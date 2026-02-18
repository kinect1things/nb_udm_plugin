from utilities.choices import ChoiceSet


class SourceStatusChoices(ChoiceSet):
    STATUS_ACTIVE = 'active'
    STATUS_DISABLED = 'disabled'

    CHOICES = [
        (STATUS_ACTIVE, 'Active', 'green'),
        (STATUS_DISABLED, 'Disabled', 'gray'),
    ]


class ScanJobStatusChoices(ChoiceSet):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    CHOICES = [
        (STATUS_PENDING, 'Pending', 'cyan'),
        (STATUS_RUNNING, 'Running', 'blue'),
        (STATUS_COMPLETED, 'Completed', 'green'),
        (STATUS_FAILED, 'Failed', 'red'),
    ]


class ResultStatusChoices(ChoiceSet):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_AUTO_APPLIED = 'auto_applied'

    CHOICES = [
        (STATUS_PENDING, 'Pending Review', 'yellow'),
        (STATUS_APPROVED, 'Approved', 'green'),
        (STATUS_REJECTED, 'Rejected', 'red'),
        (STATUS_AUTO_APPLIED, 'Auto-Applied', 'cyan'),
    ]


class ResultActionChoices(ChoiceSet):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_SKIP = 'skip'

    CHOICES = [
        (ACTION_CREATE, 'Create', 'green'),
        (ACTION_UPDATE, 'Update', 'blue'),
        (ACTION_SKIP, 'Skip', 'gray'),
    ]


class DiscoveredTypeChoices(ChoiceSet):
    TYPE_DEVICE = 'device'
    TYPE_IP_ADDRESS = 'ip_address'
    TYPE_VLAN = 'vlan'

    CHOICES = [
        (TYPE_DEVICE, 'Device', 'blue'),
        (TYPE_IP_ADDRESS, 'IP Address', 'cyan'),
        (TYPE_VLAN, 'VLAN', 'orange'),
    ]
