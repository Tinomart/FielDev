/*
FielDev: field-driven design

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/
#pragma once

#include <QDateTime>
#include <QHash>
#include <QList>
#include <QOpenGLBuffer>
#include <QOpenGLFunctions>
#include <QOpenGLShaderProgram>
#include <QOpenGLVertexArrayObject>

#include "fieldev/settings.hpp"

namespace FielDev {

class Camera;

/*
 *  The pictures to model over (the reference_image(...) calls of the script): each is a quad standing in its plane in the scene, textured with the picture, drawn after the
 *  backdrop and before the models -- the camera is free, so the picture is seen from any side, in perspective, and the models are in front of it.  A shader of its own with
 *  nothing but the matrix, the picture and its opacity, as the backdrop has: nothing of the models' state is read
 */
class ReferenceLayer : public QOpenGLFunctions
{
public:
    void initializeGL();

    /*  The pictures to draw now (the script's).  Returns whether they differ from the ones that were drawn  */
    bool set(const QList<ReferenceImage>& images);

    /*  Draws them.  `lo` and `hi` are the render region: a picture with no height of its own is as tall as the region is along its up  */
    void draw(const Camera& camera, const QVector3D& lo, const QVector3D& hi);

    bool isEmpty() const { return m_images.isEmpty(); }

protected:
    struct Picture
    {
        GLuint texture = 0;
        int width = 0, height = 0;
        qint64 size = -1;
        QDateTime modified;
    };
    /*  The texture of a file: loaded again when the file has changed (the picture is edited while it is modelled over)  */
    const Picture* picture(const QString& path);

    QList<ReferenceImage> m_images;
    QHash<QString, Picture> m_pictures;
    QOpenGLBuffer m_vbo;
    QOpenGLVertexArrayObject m_vao;
    QOpenGLShaderProgram m_program;
    bool m_ready = false;
};

}   // namespace FielDev
