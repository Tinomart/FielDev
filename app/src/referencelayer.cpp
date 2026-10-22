/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#include "fieldev/referencelayer.hpp"

#include <QFileInfo>
#include <QImage>
#include <QMatrix4x4>
#include <algorithm>
#include <cmath>
#include <cstdio>

#include "fieldev/camera.hpp"

namespace FielDev {

void ReferenceLayer::initializeGL()
{
    initializeOpenGLFunctions();

    m_vbo.create();
    m_vbo.bind();
    m_vbo.allocate(4 * 5 * int(sizeof(GLfloat)));
    m_vao.create();
    m_vao.bind();
    // (x y z, then the place in the picture: s along its right, t along its up)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(GLfloat), (GLvoid*)0);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(GLfloat), (GLvoid*)(3 * sizeof(GLfloat)));
    glEnableVertexAttribArray(0);
    glEnableVertexAttribArray(1);
    m_vbo.release();
    m_vao.release();

    m_program.addShaderFromSourceCode(QOpenGLShader::Vertex,
        "#version 150\n"
        "in vec3 vertex_position;\n"
        "in vec2 vertex_uv;\n"
        "uniform mat4 m;\n"
        "out vec2 uv;\n"
        "void main() { uv = vertex_uv; gl_Position = m * vec4(vertex_position, 1.0); }\n");
    m_program.addShaderFromSourceCode(QOpenGLShader::Fragment,
        "#version 150\n"
        "in vec2 uv;\n"
        "uniform sampler2D picture;\n"
        "uniform float opacity;\n"
        "out vec4 fragColor;\n"
        "void main() { vec4 c = texture(picture, uv); fragColor = vec4(c.rgb, c.a * opacity); }\n");
    m_program.bindAttributeLocation("vertex_position", 0);
    m_program.bindAttributeLocation("vertex_uv", 1);
    m_ready = m_program.link();
    if (!m_ready) std::fprintf(stderr, "reference images: the shader did not link: %s\n", m_program.log().toUtf8().constData());
}

bool ReferenceLayer::set(const QList<ReferenceImage>& images)
{
    if (images == m_images) return false;
    m_images = images;
    return true;
}

const ReferenceLayer::Picture* ReferenceLayer::picture(const QString& path)
{
    const QFileInfo info(path);
    auto found = m_pictures.find(path);
    if (found != m_pictures.end() && found->size == info.size() && found->modified == info.lastModified()) return found->texture ? &*found : nullptr;

    // (a file that is new, or has changed: read again)
    Picture pic;
    pic.size = info.size();
    pic.modified = info.lastModified();
    if (found != m_pictures.end() && found->texture)
    {
        glDeleteTextures(1, &found->texture);
    }
    QImage image(path);
    if (!image.isNull())
    {
        // (row 0 of the texture is the bottom of the picture: t runs along its up)
        image = image.convertToFormat(QImage::Format_RGBA8888).mirrored(false, true);
        pic.width = image.width();
        pic.height = image.height();
        glGenTextures(1, &pic.texture);
        glBindTexture(GL_TEXTURE_2D, pic.texture);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, pic.width, pic.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image.constBits());
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glBindTexture(GL_TEXTURE_2D, 0);
    }
    else
    {
        std::fprintf(stderr, "reference images: %s cannot be read as a picture\n", path.toUtf8().constData());
    }
    m_pictures[path] = pic;
    return pic.texture ? &m_pictures[path] : nullptr;
}

void ReferenceLayer::draw(const Camera& camera, const QVector3D& lo, const QVector3D& hi)
{
    if (!m_ready || m_images.isEmpty()) return;

    // (the state of a blended quad, set here and not taken from whatever the last draw left; the depth of the frame is cleared after it, so the models are in front)
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    // (blended over the backdrop; the frame's own alpha is left as it is -- the widget is composited by it, and a picture that lowered it would show the window behind through the picture)
    glEnable(GL_BLEND);
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ZERO, GL_ONE);

    m_program.bind();
    m_program.setUniformValue("m", camera.M());
    m_program.setUniformValue("picture", 0);
    glActiveTexture(GL_TEXTURE0);
    m_vao.bind();
    for (const ReferenceImage& image : m_images)
    {
        if (!image.visible || image.opacity <= 0.0f) continue;
        const Picture* pic = picture(image.path);
        if (!pic || pic->height <= 0) continue;

        // The picture's size in mm: `height` along its up (none given: as tall as the region is along it), the width in the picture's own shape
        float height = image.height;
        if (height <= 0)
        {
            const QVector3D span = hi - lo;
            height = std::fabs(image.v.x()) * span.x() + std::fabs(image.v.y()) * span.y() + std::fabs(image.v.z()) * span.z();
            if (!(height > 0)) height = 100.0f;
        }
        height *= image.scale;
        const float width = height * float(pic->width) / float(pic->height);
        const QVector3D right = image.u * (0.5f * width), up = image.v * (0.5f * height);
        const float s0 = image.flip ? 1.0f : 0.0f, s1 = image.flip ? 0.0f : 1.0f;
        const QVector3D corner[4] = {image.center - right - up, image.center - right + up, image.center + right - up, image.center + right + up};
        const float uv[4][2] = {{s0, 0.0f}, {s0, 1.0f}, {s1, 0.0f}, {s1, 1.0f}};
        GLfloat data[20];
        for (int k = 0; k < 4; ++k)
        {
            data[5 * k + 0] = corner[k].x();
            data[5 * k + 1] = corner[k].y();
            data[5 * k + 2] = corner[k].z();
            data[5 * k + 3] = uv[k][0];
            data[5 * k + 4] = uv[k][1];
        }
        m_vbo.bind();
        m_vbo.write(0, data, int(sizeof(data)));
        m_vbo.release();
        m_program.setUniformValue("opacity", image.opacity);
        glBindTexture(GL_TEXTURE_2D, pic->texture);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    m_vao.release();
    m_program.release();
    glDisable(GL_BLEND);
}

}   // namespace FielDev
