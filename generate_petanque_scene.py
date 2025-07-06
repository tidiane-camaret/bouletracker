# generate scene :
# ./blender --background --python /work/dlclarge2/ndirt-SegFM3D/bouletracker/generate_petanque_scene.py -- 1

import bpy
import bmesh
import mathutils
import random
import math
import json
import os
inmport 

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def create_petanque_field():
    """Create the pétanque field (terrain)"""
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    field = bpy.context.object
    field.name = "PetanqueField"
    
    # Add material
    mat = bpy.data.materials.new(name="FieldMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    # Add principled BSDF
    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.7, 0.5, 0.3, 1.0)  # Sandy color
    bsdf.inputs['Roughness'].default_value = 0.8
    
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    field.data.materials.append(mat)
    return field

def create_boule(location, name="Boule"):
    """Create a pétanque boule (metal ball)"""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.037, location=location)  # ~74mm diameter
    boule = bpy.context.object
    boule.name = name
    
    # Add metallic material
    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.9, 1.0)  # Metallic color
    bsdf.inputs['Metallic'].default_value = 0.9
    bsdf.inputs['Roughness'].default_value = 0.1
    
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    boule.data.materials.append(mat)
    return boule

def create_cochonnet(location):
    """Create the cochonnet (jack/target ball)"""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.015, location=location)  # ~30mm diameter
    cochonnet = bpy.context.object
    cochonnet.name = "Cochonnet"
    
    # Add wooden material
    mat = bpy.data.materials.new(name="CochonnetMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    
    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.8, 0.6, 0.2, 1.0)  # Wooden color
    bsdf.inputs['Roughness'].default_value = 0.7
    
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    cochonnet.data.materials.append(mat)
    return cochonnet

def setup_lighting():
    """Setup realistic lighting"""
    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.object
    sun.data.energy = 3
    sun.data.angle = math.radians(5)
    
    # Add area light for fill
    bpy.ops.object.light_add(type='AREA', location=(-3, -3, 5))
    area = bpy.context.object
    area.data.energy = 1
    area.data.size = 2

def generate_random_scene():
    """Generate a random pétanque scene"""
    scene_data = {
        "boules": [],
        "cochonnet": None,
        "distances": {}
    }
    
    # Create field
    create_petanque_field()
    
    # Place cochonnet randomly
    cochonnet_pos = (
        random.uniform(-3, 3),
        random.uniform(-3, 3),
        0.015  # Radius above ground
    )
    create_cochonnet(cochonnet_pos)
    scene_data["cochonnet"] = cochonnet_pos
    
    # Place 6-12 boules randomly
    num_boules = random.randint(6, 12)
    boule_positions = []
    
    for i in range(num_boules):
        # Ensure boules don't overlap
        attempts = 0
        while attempts < 50:
            pos = (
                random.uniform(-4, 4),
                random.uniform(-4, 4),
                0.037  # Radius above ground
            )
            
            # Check distance from other boules and cochonnet
            too_close = False
            for existing_pos in boule_positions + [cochonnet_pos]:
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(pos, existing_pos)))
                if dist < 0.1:  # Minimum 10cm apart
                    too_close = True
                    break
            
            if not too_close:
                break
            attempts += 1
        
        boule = create_boule(pos, f"Boule_{i+1}")
        boule_positions.append(pos)
        scene_data["boules"].append({"name": f"Boule_{i+1}", "position": pos})
    
    # Calculate all distances
    all_positions = {"cochonnet": cochonnet_pos}
    for i, pos in enumerate(boule_positions):
        all_positions[f"boule_{i+1}"] = pos
    
    for name1, pos1 in all_positions.items():
        for name2, pos2 in all_positions.items():
            if name1 != name2:
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(pos1, pos2)))
                scene_data["distances"][f"{name1}_to_{name2}"] = dist
    
    return scene_data

def setup_camera_sequence(num_frames=30):
    """Setup camera for smooth circular movement"""
    # Add camera
    bpy.ops.object.camera_add(location=(6, -6, 2))
    camera = bpy.context.object
    
    # Point camera at center of field
    constraint = camera.constraints.new(type='TRACK_TO')
    
    # Create empty object at field center for camera to track
    bpy.ops.object.empty_add(location=(0, 0, 0))
    target = bpy.context.object
    target.name = "CameraTarget"
    constraint.target = target
    
    # Set camera as active
    bpy.context.scene.camera = camera
    
    # Animate camera smoothly around the field
    for frame in range(num_frames + 1):
        bpy.context.scene.frame_set(frame)
        
        # Complete 1.5 circles around the field
        angle = (frame / num_frames) * 3 * math.pi
        radius = 7 + 2 * math.sin(frame / num_frames * 2 * math.pi)  # Varying radius
        height = 2 + 1 * math.sin(frame / num_frames * 4 * math.pi)  # Varying height
        
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = height
        
        camera.location = (x, y, z)
        camera.keyframe_insert(data_path="location")
    
    # Set interpolation to smooth
    if camera.animation_data and camera.animation_data.action:
        for fcurve in camera.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'BEZIER'
                keyframe.handle_left_type = 'AUTO'
                keyframe.handle_right_type = 'AUTO'

def render_video(output_dir, scene_name):
    """Render the video with moving camera - fast settings"""
    # Set render settings for fast video
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Much faster than Cycles
    bpy.context.scene.render.resolution_x = 640  # Lower resolution
    bpy.context.scene.render.resolution_y = 480
    bpy.context.scene.render.resolution_percentage = 50  # 320x240 effective
    
    # EEVEE settings for speed
    bpy.context.scene.eevee.taa_render_samples = 8  # Very low samples
    #bpy.context.scene.eevee.use_bloom = False
    #bpy.context.scene.eevee.use_ssr = False  # No reflections
    #bpy.context.scene.eevee.use_motion_blur = False
    
    # Video output settings
    bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
    bpy.context.scene.render.ffmpeg.format = 'MPEG4'
    bpy.context.scene.render.ffmpeg.codec = 'H264'
    bpy.context.scene.render.ffmpeg.constant_rate_factor = 'LOW'  # Fast encode
    
    # Set output path
    bpy.context.scene.render.filepath = f"{output_dir}/{scene_name}.mp4"
    
    # Render video
    bpy.ops.render.render(animation=True)
    print(f"Video rendered: {output_dir}/{scene_name}.mp4")

# Main execution
if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    scene_id = int(sys.argv[-1]) if len(sys.argv) > 1 and sys.argv[-1].isdigit() else 1
    output_dir = os.environ.get('BOULE_OUTPUT_DIR', '/work/dlclarge2/ndirt-SegFM3D/bouletracker/bouletracker_scenes')
    
    # Setup lighting
    setup_lighting()
    
    # Generate random scene with different seed
    random.seed(scene_id * 42)
    scene_data = generate_random_scene()
    
    # Setup camera animation (2 seconds at 15fps = 30 frames)
    setup_camera_sequence(30)
    
    # Set frame range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 30
    bpy.context.scene.render.fps = 15
    
    # Save scene data as JSON for ground truth
    os.makedirs(output_dir, exist_ok=True)
    scene_name = f"scene_{scene_id:03d}"
    
    with open(f"{output_dir}/{scene_name}_groundtruth.json", "w") as f:
        json.dump(scene_data, f, indent=2)
    
    print(f"Scene {scene_id} generated! Ground truth saved.")
    print(f"Cochonnet at: {scene_data['cochonnet']}")
    print(f"Number of boules: {len(scene_data['boules'])}")
    
    # Auto-render video in headless mode
    render_video(output_dir, scene_name)
    print(f"Video rendering complete: {output_dir}/{scene_name}.mp4")