"""
IDA plugin for annotate_lineinfo

Copyright (c) 2019 Branden Clark [github.com/clarkb7]
MIT License, see LICENSE for details.
"""
import idaapi
import annotate_lineinfo.annotate_lineinfo as ali

PLUGIN_COMMENT = "Annotate IDA with source and line number information from a PDB"
PLUGIN_HELP = "github.com/clarkb7/annotate_lineinfo"
PLUGIN_NAME = "annotate_lineinfo"
PLUGIN_WANTED_HOTKEY = 'Alt-A'

ali_plugin = None
try:
    idaapi.action_handler_t
except AttributeError:
    idaapi.msg("[annotate_lineinfo] IDA action API unavailable")
    ALI_IDA_ACTION_API = False
else:
    ALI_IDA_ACTION_API = True
    class ALI_DISASM_SelectionHandler(idaapi.action_handler_t):
        """Dynamic action handler. Annotate selection with line info"""
        def activate(self, ctx):
            try:
                # from is a reserved keyword in python...
                cur_sel_from = getattr(ctx.cur_sel, "from")
                start,end = (x.at.toea() for x in [cur_sel_from, ctx.cur_sel.to])
            except AttributeError:
                _,start,end = idaapi.read_selection()
            length = end-start
            ali.ida_add_lineinfo_comment_to_range(ali_plugin.dia, start, length)

    class ALI_DISASM_FunctionHandler(idaapi.action_handler_t):
        """Dynamic action handler. Annotate function with line info"""
        def activate(self, ctx):
            ida_func = ctx.cur_func
            ali.ida_add_lineinfo_comment_to_func(ali_plugin.dia, ida_func)

    class ALI_FUNCS_Handler(idaapi.action_handler_t):
        """Action handler. Annotate function with line info"""
        def activate(self, ctx):
            for pfn_id in ctx.chooser_selection:
                ida_func = idaapi.getn_func(pfn_id-1)
                ali.ida_add_lineinfo_comment_to_func(ali_plugin.dia, ida_func)
            return 1
        def update(self, ctx):
            return idaapi.AST_ENABLE_FOR_FORM

    class ALI_Hooks(idaapi.UI_Hooks):
        def finish_populating_tform_popup(self, form, popup):
            tft = idaapi.get_tform_type(form)
            if tft == idaapi.BWN_DISASM: # Disassembly view
                desc = None
                # Choose either selection or function annotation depending on cursor
                selection = idaapi.read_selection()
                if selection[0] == True:
                    desc = idaapi.action_desc_t(None,
                        'Annotate selection with line info', ALI_DISASM_SelectionHandler())
                else:
                    func = idaapi.get_func(ScreenEA())
                    if func is not None:
                        desc = idaapi.action_desc_t(None,
                            'Annotate function with line info', ALI_DISASM_FunctionHandler())
                # Add corresponding action to popup menu
                if desc is not None:
                    idaapi.attach_dynamic_action_to_popup(form, popup, desc, None)
            elif tft == idaapi.BWN_FUNCS: # Functions view
                # Add action to popup menu
                idaapi.attach_action_to_popup(form, popup,
                    type(ali_plugin).action_wfuncs_name, None,
                    idaapi.SETMENU_INS)

class ALI_plugin_t(idaapi.plugin_t):
    flags = idaapi.PLUGIN_PROC
    comment = PLUGIN_COMMENT
    help = PLUGIN_HELP
    wanted_name = PLUGIN_NAME
    wanted_hotkey = PLUGIN_WANTED_HOTKEY

    action_wfuncs_name = 'ali:wfuncs'
    action_wfuncs_label = "Annotate function(s) with line info"
    def init(self):
        self.dia = None
        self.hooks = None

        idaapi.autoWait()
        if idaapi.get_input_file_path() is None:
            idaapi.msg("[annotate_lineinfo] No file loaded")
            return idaapi.PLUING_SKIP
        idaapi.msg("[annotate_lineinfo] loaded!\n")

        try:
            self.dia = ali.DIASession(idaapi.get_input_file_path())
        except ValueError as e:
            idaapi.msg("[annotate_lineinfo] Unable to load PDB: {}".format(e))
            return idaapi.PLUGIN_SKIP

        if ALI_IDA_ACTION_API:
            # Setup/register UI_HOOKs
            self.hooks = ALI_Hooks()
            if not self.hooks.hook():
                idaapi.msg("[annotate_lineinfo] Failed to install UI hooks")
                return idaapi.PLUGINSKIP
            # Register actions
            action_desc = idaapi.action_desc_t(
                type(self).action_wfuncs_name, type(self).action_wfuncs_label,
                ALI_FUNCS_Handler())
            if not idaapi.register_action(action_desc):
                idaapi.msg("[annotate_lineinfo] Failed to register action: {}".format(
                    type(self).action_wfuncs_name))
                return idaapi.PLUGIN_SKIP

        return idaapi.PLUGIN_KEEP

    def run(self, arg):
        ali.ida_annotate_lineinfo_dia(self.dia)

    def term(self):
        idaapi.msg("[annotate_lineinfo] unloading!\n")
        if ALI_IDA_ACTION_API:
            if self.hooks is not None:
                self.hooks.unhook()
            idaapi.unregister_action(type(self).action_wfuncs_name)

def PLUGIN_ENTRY():
    global ali_plugin
    ali_plugin = ALI_plugin_t()
    return ali_plugin

