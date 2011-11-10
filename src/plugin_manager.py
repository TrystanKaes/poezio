import imp
import os
import sys
import tabs
from config import config
from gettext import gettext as _

plugins_dir = config.get('plugins_dir', '')
plugins_dir = plugins_dir or\
    os.path.join(os.environ.get('XDG_DATA_HOME') or\
                     os.path.join(os.environ.get('HOME'), '.local', 'share'),
                 'poezio', 'plugins')

config_home = os.environ.get("XDG_CONFIG_HOME")
if not config_home:
    config_home = os.path.join(os.environ.get('HOME'), '.config')
plugins_conf_dir = os.path.join(config_home, 'poezio', 'plugins')

try:
    os.makedirs(plugins_dir)
except OSError:
    pass

try:
    os.makedirs(plugins_conf_dir)
except OSError:
    pass

sys.path.append(plugins_dir)

class PluginManager(object):
    def __init__(self, core):
        self.core = core
        self.modules = {} # module name -> module object
        self.plugins = {} # module name -> plugin object
        self.commands = {} # module name -> dict of commands loaded for the module
        self.event_handlers = {} # module name -> list of event_name/handler pairs loaded for the module
        self.tab_commands = {} #module name -> dict of tab types; tab type -> commands loaded by the module

    def load(self, name):
        if name in self.plugins:
            self.unload(name)

        try:
            if name in self.modules:
                imp.acquire_lock()
                module = imp.reload(self.modules[name])
                imp.release_lock()
            else:
                file, filename, info = imp.find_module(name, [plugins_dir])
                imp.acquire_lock()
                module = imp.load_module(name, file, filename, info)
                imp.release_lock()
        except Exception as e:
            import traceback
            self.core.information(_("Could not load plugin: ") + traceback.format_exc(), 'Error')
            return
        finally:
            if imp.lock_held():
                imp.release_lock()

        self.modules[name] = module
        self.commands[name] = {}
        self.tab_commands[name] = {}
        self.event_handlers[name] = []
        self.plugins[name] = module.Plugin(self, self.core, plugins_conf_dir)
        self.core.information('Plugin %s loaded' % name, 'Info')

    def unload(self, name):
        if name in self.plugins:
            try:
                for command in self.commands[name].keys():
                    del self.core.commands[command]
                for tab in list(self.tab_commands[name].keys()):
                    for command in self.tab_commands[name][tab]:
                        self.del_tab_command(name, getattr(tabs, tab), command[0])
                    del self.tab_commands[name][tab]
                for event_name, handler in self.event_handlers[name]:
                    self.del_event_handler(name, event_name, handler)

                self.plugins[name].unload()
                del self.plugins[name]
                del self.commands[name]
                del self.tab_commands[name]
                del self.event_handlers[name]
                self.core.information('Plugin %s unloaded' % name, 'Info')
            except Exception as e:
                import traceback
                self.core.information(_("Could not unload plugin (may not be safe to try again): ") + traceback.format_exc())

    def del_command(self, module_name, name):
        if name in self.commands[module_name]:
            del self.commands[module_name][name]
            if name in self.core.commands:
                del self.core.commands[name]

    def add_tab_command(self, module_name, tab_type, name, handler, help, completion=None):
        commands = self.tab_commands[module_name]
        t = tab_type.__name__
        if not t in commands:
            commands[t] = []
        commands[t].append((name, handler, help, completion))
        for tab in self.core.tabs:
            if isinstance(tab, tab_type):
                tab.add_plugin_command(name, handler, help, completion)

    def del_tab_command(self, module_name, tab_type, name):
        commands = self.tab_commands[module_name]
        t = tab_type.__name__
        if not t in commands:
            return
        for command in commands[t]:
            if command[0] == name:
                commands[t].remove(command)
                del tab_type.plugin_commands[name]
                for tab in self.core.tabs:
                    if isinstance(tab, tab_type) and name in tab.commands:
                        del tab.commands[name]

    def add_command(self, module_name, name, handler, help, completion=None):
        if name in self.core.commands:
            raise Exception(_("Command '%s' already exists") % (name,))

        commands = self.commands[module_name]
        commands[name] = (handler, help, completion)
        self.core.commands[name] = (handler, help, completion)

    def add_event_handler(self, module_name, event_name, handler, position=0):
        eh = self.event_handlers[module_name]
        eh.append((event_name, handler))
        if event_name in self.core.events.events:
            self.core.events.add_event_handler(event_name, handler, position)
        else:
            self.core.xmpp.add_event_handler(event_name, handler)

    def del_event_handler(self, module_name, event_name, handler):
        if event_name in self.core.events.events:
            self.core.events.del_event_handler(None, handler)
        else:
            self.core.xmpp.del_event_handler(event_name, handler)
        eh = self.event_handlers[module_name]
        eh = list(filter(lambda e : e != (event_name, handler), eh))

    def completion_load(self, the_input):
        """
        completion function that completes the name of the plugins, from
        all .py files in plugins_dir
        """
        try:
            names = os.listdir(plugins_dir)
        except OSError as e:
            self.core.information(_('Completion failed: %s' % e), 'Error')
            return
        plugins_files = [name[:-3] for name in names if name.endswith('.py')]
        return the_input.auto_completion(plugins_files, '')

    def completion_unload(self, the_input):
        """
        completion function that completes the name of the plugins that are loaded
        """
        return the_input.auto_completion(list(self.plugins.keys()), '')
