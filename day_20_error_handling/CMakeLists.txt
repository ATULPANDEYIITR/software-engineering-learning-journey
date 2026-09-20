# File: CMakeLists.txt
cmake_minimum_required(VERSION 3.20)

project(
    defensive_error_handling
    VERSION 1.0.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(
    error_handling_demo
    cpp/main.cpp
)

if (MSVC)
    target_compile_options(
        error_handling_demo
        PRIVATE /W4 /permissive-
    )
else()
    target_compile_options(
        error_handling_demo
        PRIVATE -Wall -Wextra -Wpedantic -Wconversion
    )
endif()
