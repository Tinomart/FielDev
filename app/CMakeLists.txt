# The FielDev application (Qt): editor, viewport, model tree, section viewer
if (NOT DEFINED FIELDEV_BUILD_FROM_ROOT)
    message(FATAL_ERROR "CMake must be called against the top-level directory")
endif()

# Instruct CMake to run moc, uic, and rcc automatically when needed.
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt5Core REQUIRED)
find_package(Qt5Widgets REQUIRED)
find_package(Qt5OpenGL REQUIRED)
find_package(Qt5Network REQUIRED)
find_package(Qt5Concurrent REQUIRED)

set(SRCS
    src/main.cpp
    src/app.cpp
    src/appwindow.cpp
    src/args.cpp
    src/arrow.cpp
    src/automation.cpp
    src/axes.cpp
    src/background.cpp
    src/bbox.cpp
    src/busy.cpp
    src/carddrag.cpp
    src/camera.cpp
    src/color.cpp
    src/documentation.cpp
    src/editor.cpp
    src/fileassoc.cpp
    src/findbar.cpp
    src/focuscue.cpp
    src/i18n.cpp
    src/icons.cpp
    src/language.cpp
    src/primitives_dialog.cpp
    src/referencelayer.cpp
    src/scenetree.cpp
    src/script.cpp
    src/section.cpp
    src/settings.cpp
    src/shader.cpp
    src/shortcuts.cpp
    src/shape.cpp
    src/symmetry.cpp
    src/materialspanel.cpp
    src/syntax.cpp
    src/theme.cpp
    src/tutorial.cpp
    src/typeicons.cpp
    src/view.cpp
    src/window.cpp
    src/workplane.cpp

    src/python/formatter.cpp
    src/python/interpreter.cpp
    src/python/language.cpp
    src/python/syntax.cpp

    resources.qrc
)

set(QOBJECTS
    include/fieldev/app.hpp
    include/fieldev/appwindow.hpp
    include/fieldev/automation.hpp
    include/fieldev/busy.hpp
    include/fieldev/camera.hpp
    include/fieldev/documentation.hpp
    include/fieldev/editor.hpp
    include/fieldev/findbar.hpp
    include/fieldev/interpreter.hpp
    include/fieldev/language.hpp
    include/fieldev/primitives_dialog.hpp
    include/fieldev/scenetree.hpp
    include/fieldev/script.hpp
    include/fieldev/section.hpp
    include/fieldev/carddrag.hpp
    include/fieldev/focuscue.hpp
    include/fieldev/shape.hpp
    include/fieldev/shortcuts.hpp
    include/fieldev/symmetry.hpp
    include/fieldev/materialspanel.hpp
    include/fieldev/syntax.hpp
    include/fieldev/tutorial.hpp
    include/fieldev/view.hpp
    include/fieldev/window.hpp
    include/fieldev/workplane.hpp
)

if(WIN32)
    add_executable(FielDev WIN32 ${SRCS} ${QOBJECTS} deploy/windows/icon.rc)
    # (the icon is in the resource file by its name: the resource is made again when the .ico changes -- the build did not see that by itself, and the exe kept the first icon through every
    # new one, the old FielDes icon, until a new logo was looked at in the exe)
    set_source_files_properties(deploy/windows/icon.rc PROPERTIES OBJECT_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/deploy/windows/fieldev.ico)
else()
    add_executable(FielDev ${SRCS} ${QOBJECTS})
endif()

# Where FielDev.exe is built: set FIELDEV_OUTPUT_DIR to the folder the program is run from (dist/FielDev) and it is built straight into it -- the libraries are put beside it by the
# steps below -- so that there is no copy of the build to make.  Empty: in the build tree, as ever.  (A running FielDev.exe cannot be replaced: close it before the link step.)
set(FIELDEV_OUTPUT_DIR "" CACHE PATH "Where FielDev.exe is built (empty: in the build tree)")
if(FIELDEV_OUTPUT_DIR)
    set_target_properties(FielDev PROPERTIES RUNTIME_OUTPUT_DIRECTORY_RELEASE "${FIELDEV_OUTPUT_DIR}")
endif()

target_include_directories(FielDev PUBLIC include)
if(MSVC)
    # a map of where the functions are: a crash report names places as module + offset, read with it (kept in the build folder: with FIELDEV_OUTPUT_DIR the
    # program is built into the folder it is run from, and the map is not a part of it)
    target_link_options(FielDev PRIVATE "/MAP:${CMAKE_CURRENT_BINARY_DIR}/FielDev.map")
endif()
target_include_directories(FielDev PRIVATE ${Python3_INCLUDE_DIRS})
target_link_libraries(FielDev
    libfive libfive-stdlib
    ${Python3_LIBRARIES}
    Qt5::Widgets
    Qt5::Gui
    Qt5::OpenGL
    Qt5::Concurrent
)
target_compile_definitions(FielDev PRIVATE FIELDEV_WITH_PYTHON FIELDEV_VERSION="${PROJECT_VERSION}")

if (MSVC)
    # Copy the DLLs into the build directory, so that FielDev.exe can find them
    add_custom_command(TARGET FielDev POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:libfive>
            $<TARGET_FILE_DIR:FielDev>)
    add_custom_command(TARGET FielDev POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:libfive-stdlib>
            $<TARGET_FILE_DIR:FielDev>)
    # The kernel's own dependency (manifold.dll): FielDev.exe doesn't link
    # it directly, so vcpkg's app-local copy step doesn't bring it
    find_package(manifold CONFIG REQUIRED)
    add_custom_command(TARGET FielDev POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:manifold::manifold>
            $<TARGET_FILE_DIR:FielDev>)
endif(MSVC)
