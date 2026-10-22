# The kernel: field evaluation and meshing (shared library "fieldev"),
# and its C++ standard library of shapes ("fieldev-stdlib")
if (NOT DEFINED FIELDEV_BUILD_FROM_ROOT)
    message(FATAL_ERROR "CMake must be called against the top-level directory")
endif()

add_subdirectory(src)
add_subdirectory(stdlib)
