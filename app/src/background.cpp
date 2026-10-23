/*
FielDev: field-driven design
Derived from Studio, a simple GUI for the libfive CAD kernel
Copyright (C) 2017  Matt Keeter

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
*/
#include "fieldev/background.hpp"

namespace FielDev {

// (the viewport's backdrop, a toy box's sky: deep indigo below, violet above and a touch of bubblegum at the top right -- lighter than the cards on it)
#define SKY_BL 0.1647, 0.1451, 0.4118
#define SKY_BR 0.1608, 0.2314, 0.5255
#define SKY_TL 0.3569, 0.2118, 0.6588
#define SKY_TR 0.6196, 0.2706, 0.6588

void Background::initializeGL()
{
    initializeOpenGLFunctions();

    {
        // Data is arranged  x   y   z   r   g   b
        GLfloat data[] = {   /********************/
                            -1, -1,  0.9,  SKY_BL,
                            -1,  1,  0.9,  SKY_TL,
                             1, -1,  0.9,  SKY_BR,
                             1,  1,  0.9,  SKY_TR,
        };
        vbo.create();
        vbo.bind();
        vbo.allocate(data, sizeof(data));

        vao.create();
        vao.bind();

        // Data stored in VAO
        glVertexAttribPointer(
                0, 3, GL_FLOAT, GL_FALSE,
                6 * sizeof(GLfloat), (GLvoid*)0);
        glVertexAttribPointer(
                1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(GLfloat),
                (GLvoid*)(3 * sizeof(GLfloat)));
        glEnableVertexAttribArray(0);
        glEnableVertexAttribArray(1);

        vbo.release();
        vao.release();
    }

    // (nothing but the position and the colour: no uniform, nothing to read that another draw could have left set)
    program.addShaderFromSourceCode(QOpenGLShader::Vertex,
        "#version 150\n"
        "in vec3 vertex_position;\n"
        "in vec3 vertex_color;\n"
        "out vec3 sky;\n"
        "void main() { sky = vertex_color; gl_Position = vec4(vertex_position.xy, 0.0, 1.0); }\n");
    program.addShaderFromSourceCode(QOpenGLShader::Fragment,
        "#version 150\n"
        "in vec3 sky;\n"
        "out vec4 fragColor;\n"
        "void main() { fragColor = vec4(sky, 1.0); }\n");
    program.bindAttributeLocation("vertex_position", 0);
    program.bindAttributeLocation("vertex_color", 1);
    ready = program.link();
}

void Background::draw()
{
    if (!ready) return;
    // (the state a quad over the whole of the view needs, set here and not taken from whatever the last draw left)
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_BLEND);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);

    program.bind();
    vao.bind();
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    vao.release();
    program.release();
}

}   // namespace FielDev
