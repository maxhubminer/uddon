bl_info = {
    "name": "Uddon",
    "author": "Aleksey Shishkin",
    "version": (0, 1, 0),
    "blender": (2, 92, 0),
    "location": "Object > Uddon",
    "description": "Exports fbx according to selected object(s)/collection name",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    # "support": '',
    "category": "Import-Export",
}

import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty


class Uddon(AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    exportpath: StringProperty(
        name="Fbx export path (folder)",
        subtype='DIR_PATH',
    )
    applyOnExport: BoolProperty(
        name="Apply scaling/smoothing on export. If not - just warn about it",
        default=True,
    )
    applyScaling: BoolProperty(
        name="Scale to 1 on export?",
        default=True,
    )
    applySmoothing: BoolProperty(
        name="Shade Smooth on export?",
        default=True,
    )
    suffixDraft: StringProperty(
        name="Draft suffix",
        default='.draft',
    )
    suffixLP: StringProperty(
        name="Low-poly suffix",
        default='.lp',
    )
    suffixHP: StringProperty(
        name="High-poly suffix",
        default='.hp',
    )

    # number: IntProperty(
    #     name="Example Number",
    #     default=4,
    # )

    def draw(self, context):
        layout = self.layout
        # layout.label(text="Set your preferences")
        layout.prop(self, "exportpath")
        layout.prop(self, "applyOnExport")
        layout.prop(self, "applyScaling")
        layout.prop(self, "applySmoothing")
        layout.prop(self, "suffixDraft")
        layout.prop(self, "suffixLP")
        layout.prop(self, "suffixHP")


def preferences(context):
    preferences = context.preferences
    addon_prefs = preferences.addons[__name__].preferences

    info = ("Path: %s, Scaling: %d, Smoothing %r" %
            (addon_prefs.exportpath, addon_prefs.applyScaling, addon_prefs.applySmoothing))

    print(info)

    return addon_prefs


def get_collection_parent(collection_name, master_collection):
    for coll in bpy.data.collections:
        if collection_name in coll.children.keys():
            return coll
    return master_collection

def duplicate_collection_objects(original_copy_objectmap, collection, collection_new, suffix_XP):
    for obj in collection.objects:
        obj_new = obj.copy()
        obj_new.name = obj_new.name[:-4] + suffix_XP  # minus 4 digits on the right + suffix
        collection_new.objects.link(obj_new)
        original_copy_objectmap[obj] = obj_new

def parent_objects(original_copy_objectmap):
    for orig, copy in original_copy_objectmap.items():
        orig_parent = orig.parent
        if not (orig_parent is None):
            savedState = copy.matrix_world
            copy.parent = original_copy_objectmap[orig_parent]
            copy.matrix_world = savedState

def duplicate_collection_hierarchy(original_copy_objectmap, collection, collection_new, suffix_draft, suffix_XP):
    for coll in collection.children:
        basename = collection_basename(coll.name, suffix_draft)
        curIterationColl = bpy.data.collections.new(f"{basename}{suffix_XP}")
        collection_new.children.link(curIterationColl)

        duplicate_collection_objects(original_copy_objectmap, coll, curIterationColl, suffix_XP)

        duplicate_collection_hierarchy(original_copy_objectmap, coll, curIterationColl, suffix_draft, suffix_XP)

def collection_basename(collection_name, suffix_draft):
    basename = ''
    draft_ind = collection_name.find(suffix_draft)
    if draft_ind != -1:
        basename = collection_name[:draft_ind]
    else:
        basename = collection_name

    return basename

def duplicate_collection(suffix_draft, suffix_XP, collection, master_collection):

    collection_name = collection.name

    basename = collection_basename(collection_name, suffix_draft)

    collection_new = bpy.data.collections.new(f"{basename}{suffix_XP}")

    # link new collection to the same parent as original collection
    parent_coll = get_collection_parent(collection_name, master_collection)
    parent_coll.children.link(collection_new)

    original_copy_objectmap = {}

    # duplicate first-level collection objects
    duplicate_collection_objects(original_copy_objectmap, collection, collection_new, suffix_XP)
    # duplicate collection hierarchy
    duplicate_collection_hierarchy(original_copy_objectmap, collection, collection_new, suffix_draft, suffix_XP)

    parent_objects(original_copy_objectmap)


def duplicate_collection2():
    for window in bpy.context.window_manager.windows:
        screen = window.screen

        for area in screen.areas:
            if area.type == 'OUTLINER':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.outliner.collection_duplicate(override)
                break

class ExportCollection(bpy.types.Operator):
    """(uddon) Export collection"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_exportcollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Export collection"  # Display name in the interface.

    # bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.

        scene = context.scene
        collection = context.collection
        prefs = preferences(context)

        if (prefs.exportpath == ''):
            self.report({'ERROR'}, 'Fbx export path is not set! Go to Uddon add-on preferences')
            return {'FINISHED'}
        folderpath = prefs.exportpath

        filename = collection.name
        if (filename == ''):
            self.report({'ERROR'}, 'Please select collection')
            return {'FINISHED'}

        filepath = f"{folderpath}{filename}.fbx"

        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.all_objects:
            obj.select_set(True)

        print('Exporting to filepath = ' + filepath)

        bpy.ops.export_scene.fbx(filepath=filepath,
                                 use_selection=True,
                                 use_active_collection=True)

        return {'FINISHED'}  # Lets Blender know the operator finished successfully.

    def log(self, logstring):
        print('uddon: ' + logstring)


class PrepareCollection(bpy.types.Operator):
    """(uddon) Prepare collection"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_preparecollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Prepare collection"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.

        collection = context.collection
        prefs = preferences(context)

        if (prefs.applyOnExport):
            bpy.ops.object.select_all(action='DESELECT')
            for obj in collection.all_objects:
                obj.select_set(True)

            if prefs.applyScaling:
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True, properties=False)
            if prefs.applySmoothing:
                bpy.ops.object.shade_smooth()

        return {'FINISHED'}  # Lets Blender know the operator finished successfully.


class CreateCollectionLP(bpy.types.Operator):
    """(uddon) Create LP collection"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_lpcollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Create LP collection"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.

        scene = context.scene
        master_collection = scene.collection
        collection = context.collection
        collection_name = context.collection.name
        prefs = preferences(context)

        duplicate_collection(prefs.suffixDraft, prefs.suffixLP, collection, master_collection)

        return {'FINISHED'}  # Lets Blender know the operator finished successfully.


class CreateCollectionHP(bpy.types.Operator):
    """(uddon) Create HP collection"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_hpcollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Create HP collection"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.

        scene = context.scene
        master_collection = scene.collection
        collection = context.collection
        collection_name = context.collection.name
        prefs = preferences(context)

        duplicate_collection(prefs.suffixDraft, prefs.suffixHP, collection, master_collection)

        return {'FINISHED'}  # Lets Blender know the operator finished successfully.


class SyncLPHP(bpy.types.Operator):
    """(uddon) Sync LP with HP collections"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_synclphpcollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Sync LP with HP collections"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.
        return {'FINISHED'}  # Lets Blender know the operator finished successfully.


class PrepareAndExportCollection(bpy.types.Operator):
    """(uddon) Prepare and Export collection"""  # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.uddon_prepexpcollection"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Prepare & Export collection"  # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):  # execute() is called when running the operator.

        PrepareCollection.execute(self, context)
        ExportCollection.execute(self, context)

        return {'FINISHED'}  # Lets Blender know the operator finished successfully.


### MENU

class MainMenu(bpy.types.Menu):
    bl_label = 'Uddon'
    bl_idname = 'uddon.mainmenu'

    def draw(self, context):
        layout = self.layout
        layout.operator(PrepareAndExportCollection.bl_idname)
        layout.operator(PrepareCollection.bl_idname)
        layout.operator(ExportCollection.bl_idname)
        layout.operator(CreateCollectionLP.bl_idname)
        layout.operator(CreateCollectionHP.bl_idname)
        layout.operator(SyncLPHP.bl_idname)


def draw_menu(self, context):
    self.layout.menu(MainMenu.bl_idname)


def register():
    print(f"Add-on {bl_info['name']} registered")

    bpy.utils.register_class(PrepareCollection)
    bpy.utils.register_class(ExportCollection)
    bpy.utils.register_class(CreateCollectionLP)
    bpy.utils.register_class(CreateCollectionHP)
    bpy.utils.register_class(SyncLPHP)
    bpy.utils.register_class(PrepareAndExportCollection)

    bpy.utils.register_class(Uddon)

    bpy.utils.register_class(MainMenu)
    bpy.types.VIEW3D_MT_object.append(draw_menu)  # Adds the new operator to an existing menu.


def unregister():
    print(f"Add-on {bl_info['name']} unregistered")

    bpy.types.VIEW3D_MT_object.remove(draw_menu)
    bpy.utils.unregister_class(MainMenu)

    bpy.utils.unregister_class(Uddon)

    bpy.utils.unregister_class(PrepareCollection)
    bpy.utils.unregister_class(ExportCollection)
    bpy.utils.unregister_class(CreateCollectionLP)
    bpy.utils.unregister_class(CreateCollectionHP)
    bpy.utils.unregister_class(SyncLPHP)
    bpy.utils.unregister_class(PrepareAndExportCollection)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
