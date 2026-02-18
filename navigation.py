from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton
from netbox.choices import ButtonColorChoices

menu = PluginMenu(
    label='UniFi Discovery',
    groups=(
        ('Discovery', (
            PluginMenuItem(
                link='plugins:nb_udm_plugin:dashboard',
                link_text='Dashboard',
            ),
            PluginMenuItem(
                link='plugins:nb_udm_plugin:discoverysource_list',
                link_text='Sources',
                buttons=(
                    PluginMenuButton(
                        link='plugins:nb_udm_plugin:discoverysource_add',
                        title='Add Source',
                        icon_class='mdi mdi-plus-thick',
                        color=ButtonColorChoices.GREEN,
                    ),
                ),
            ),
            PluginMenuItem(
                link='plugins:nb_udm_plugin:discoveryresult_list',
                link_text='Results',
            ),
        )),
        ('Operations', (
            PluginMenuItem(
                link='plugins:nb_udm_plugin:scanjob_list',
                link_text='Scan Jobs',
            ),
            PluginMenuItem(
                link='plugins:nb_udm_plugin:discoverymapping_list',
                link_text='Mappings',
            ),
        )),
    ),
    icon_class='mdi mdi-radar',
)
