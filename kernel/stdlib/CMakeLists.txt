add_library(libfive-stdlib SHARED stdlib.cpp stdlib_impl.cpp)

# The library is named 'fieldev-stdlib' on all platforms
set_target_properties(libfive-stdlib PROPERTIES PREFIX "" OUTPUT_NAME fieldev-stdlib)
target_link_libraries(libfive-stdlib libfive)
