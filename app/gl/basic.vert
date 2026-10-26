#version 150
#extension GL_ARB_explicit_attrib_location : require

layout(location=0) in vec3 vertex_position;
layout(location=1) in vec3 vertex_color;
layout(location=2) in vec3 vertex_norm;
// A deformed model's undeformed position: the section cuts the material
// there, so the cut moves with the deformation (use_rest != 0)
layout(location=3) in vec3 rest_position;
// A patch of a surface (patch_mode != 0 in the fragment shader): above zero, the vertex is not part of it and the
// part is not drawn there
layout(location=4) in float patch_value;
uniform int use_rest;

uniform mat4 M;

// Section view: the kept side of the cutting plane is where
// dot(position, clip_plane) >= 0 (only used while GL_CLIP_DISTANCE0 is on)
uniform vec4 clip_plane;
out float gl_ClipDistance[1];

out vec4 frag_color;
out vec3 base_pos;
out vec3 frag_pos;
out vec3 frag_norm;
out float frag_patch;
// The normal of a smoothly lit mesh (smooth_normals in the fragment shader), in the space of frag_pos: the vertex's normal carried through the whole projection by the inverse transpose of the Jacobian of the
// position, so that it holds for a perspective camera too
out vec3 frag_nrm;

void main()
{
    base_pos = vertex_position;
    frag_patch = patch_value;

    gl_Position = M * vec4(vertex_position, 1.0f);
    vec3 clip_pos = use_rest != 0 ? rest_position : vertex_position;
    gl_ClipDistance[0] = dot(vec4(clip_pos, 1.0f), clip_plane);
    gl_Position.w = max(0, gl_Position.w);

    frag_pos = gl_Position.xyz / gl_Position.w;
    frag_color = vec4(vertex_color, 1.0f);

    vec4 norm_pos = M * vec4(vertex_position + vertex_norm, 1.0f);
    frag_norm = (norm_pos.xyz / norm_pos.w) - frag_pos;
    frag_norm.z *= -8;
    frag_norm = normalize(frag_norm);

    {
        float cw = max(gl_Position.w, 1e-6);
        mat3 A = mat3(M);
        vec3 wrow = vec3(M[0][3], M[1][3], M[2][3]);
        mat3 J = (A - outerProduct(frag_pos, wrow)) / cw;
        frag_nrm = transpose(inverse(J)) * vertex_norm;
    }
}
