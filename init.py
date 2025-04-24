bl_info = {
    "name": "Blendshape Drive & Transfer",
    "blender": (4, 4, 1),
    "category": "Object",
}

import bpy
import uuid

def remove_blend_driver(obj, blend_id):
    if obj.data.shape_keys and obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.drivers:
        drivers = obj.data.shape_keys.animation_data.drivers
        driver = drivers.find(f'key_blocks["{blend_id}"].value')
        
        if driver is not None:
            drivers.remove(driver)

def make_blend_driver(base_item, blend_id, blend):
    fcurve = blend.driver_add('value')
    driver = fcurve.driver
    driver.type = 'AVERAGE'

    dvar = driver.variables.new()
    dvar.type = 'SINGLE_PROP'
    dvar.name = blend_id.replace(" ", "")

    target = dvar.targets[0]
    target.id_type = 'KEY'
    target.id = base_item.data.shape_keys
    target.data_path = f'key_blocks["{blend_id}"].value'

def transfer_blendshape_destructive(base_item, target_item, blend_id):
    with bpy.context.temp_override(object=target_item):
        # Generate surface deform modifier.
        mod_identifier = str(uuid.uuid4())
        modifier = target_item.modifiers.new(mod_identifier, 'SURFACE_DEFORM')
        modifier.target = base_item

        bpy.ops.object.surfacedeform_bind(modifier=mod_identifier)
        
        # Bake surface deform modifier.
        base_blendshape = base_item.data.shape_keys.key_blocks[blend_id]
        base_blendshape.value = 1.0
        bpy.ops.object.modifier_apply_as_shapekey(modifier=mod_identifier)
        base_blendshape.value = 0.0
        
        # Select and rename the new blendshape to our blend id.
        target_blendshape = target_item.data.shape_keys.key_blocks.values()[-1]
        target_blendshape.name = blend_id

        remove_blend_driver(target_item, blend_id)
        make_blend_driver(base_item, blend_id, target_blendshape)

class ObjectTransferShapes(bpy.types.Operator):
    """Object Transfer Shapes"""
    bl_idname = "object.transfer_shapes"
    bl_label = "Transfer Shapes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        base_item = bpy.context.active_object
        baking_items = [ o for o in bpy.context.selected_objects
                            if o.type == 'MESH'
                            and o is not base_item ]
        
        bpy.ops.object.mode_set(mode='OBJECT')

        # Generate target shape list.
        baking_keys = [key for key in base_item.data.shape_keys.key_blocks.keys() if key != "Basis"]

        # Clear existing keys.
        for obj in baking_items:
            if obj.data.shape_keys:
                for k in obj.data.shape_keys.key_blocks:
                    obj.shape_key_remove(k)
            
            for shape in baking_keys:
                transfer_blendshape_destructive(base_item, obj, shape)
        
        return {'FINISHED'}

class ObjectLinkShapes(bpy.types.Operator):
    """Object Link Shapes"""
    bl_idname = "object.link_shapes"
    bl_label = "Link Shapes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        base_item = bpy.context.active_object
        baking_items = [ o for o in bpy.context.selected_objects
                            if o.type == 'MESH'
                            and o is not base_item ]
        
        baking_keys = [key for key in base_item.data.shape_keys.key_blocks.keys() if key != "Basis"]
        for obj in baking_items:
            if obj.data.shape_keys:
                for shape in baking_keys:
                    target_key = obj.data.shape_keys.key_blocks[shape]
                    if target_key:
                        remove_blend_driver(obj, shape)
                        make_blend_driver(base_item, shape, target_key)
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(ObjectTransferShapes.bl_idname)
    self.layout.operator(ObjectLinkShapes.bl_idname)

def register():
    bpy.utils.register_class(ObjectTransferShapes)
    bpy.utils.register_class(ObjectLinkShapes)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ObjectTransferShapes)
    bpy.utils.unregister_class(ObjectLinkShapes)

if __name__ == "__main__":
    register()