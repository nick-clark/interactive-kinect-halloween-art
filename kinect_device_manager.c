/*
 * Kinect Device Manager
 * 
 * This utility follows the exact same initialization sequence as freenect-camtest
 * but is designed to prepare the Kinect device for Python scripts.
 * 
 * It claims the device, initializes it properly, then releases it cleanly
 * so that Python freenect can access it.
 */

#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "libfreenect.h"

#ifndef SIGQUIT // win32 compat
    #define SIGQUIT SIGTERM
#endif

volatile bool running = true;
void signalHandler(int signal)
{
    if (signal == SIGINT || signal == SIGTERM || signal == SIGQUIT)
    {
        running = false;
    }
}

int main(int argc, char** argv)
{
    printf("🔧 Kinect Device Manager\n");
    printf("========================\n");
    
    // Handle signals gracefully
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGQUIT, signalHandler);

    // Initialize libfreenect (same as camtest)
    freenect_context* fn_ctx;
    int ret = freenect_init(&fn_ctx, NULL);
    if (ret < 0)
    {
        printf("❌ Failed to initialize freenect context: %d\n", ret);
        return ret;
    }
    printf("✅ Freenect context initialized\n");

    // Show debug messages and use camera only (same as camtest)
    freenect_set_log_level(fn_ctx, FREENECT_LOG_DEBUG);
    freenect_select_subdevices(fn_ctx, FREENECT_DEVICE_CAMERA);
    printf("✅ Log level set and camera selected\n");

    // Find out how many devices are connected (same as camtest)
    int num_devices = freenect_num_devices(fn_ctx);
    if (num_devices < 0)
    {
        printf("❌ Failed to get device count: %d\n", num_devices);
        freenect_shutdown(fn_ctx);
        return num_devices;
    }
    if (num_devices == 0)
    {
        printf("❌ No Kinect devices found!\n");
        freenect_shutdown(fn_ctx);
        return 1;
    }
    printf("✅ Found %d Kinect device(s)\n", num_devices);

    // Open the first device (same as camtest)
    freenect_device* fn_dev;
    ret = freenect_open_device(fn_ctx, &fn_dev, 0);
    if (ret < 0)
    {
        printf("❌ Failed to open device: %d\n", ret);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Device opened successfully\n");

    // Set depth and video modes (same as camtest)
    ret = freenect_set_depth_mode(fn_dev, freenect_find_depth_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_DEPTH_MM));
    if (ret < 0)
    {
        printf("❌ Failed to set depth mode: %d\n", ret);
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Depth mode set\n");

    ret = freenect_set_video_mode(fn_dev, freenect_find_video_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_VIDEO_RGB));
    if (ret < 0)
    {
        printf("❌ Failed to set video mode: %d\n", ret);
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Video mode set\n");

    // Start depth and video streams (same as camtest)
    ret = freenect_start_depth(fn_dev);
    if (ret < 0)
    {
        printf("❌ Failed to start depth stream: %d\n", ret);
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Depth stream started\n");

    ret = freenect_start_video(fn_dev);
    if (ret < 0)
    {
        printf("❌ Failed to start video stream: %d\n", ret);
        freenect_stop_depth(fn_dev);
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Video stream started\n");

    // Let the device run for a few seconds to stabilize
    printf("🔄 Stabilizing device for 3 seconds...\n");
    int stabilization_time = 3;
    int frame_count = 0;
    
    while (running && stabilization_time > 0)
    {
        ret = freenect_process_events(fn_ctx);
        if (ret < 0)
        {
            printf("❌ Error processing events: %d\n", ret);
            break;
        }
        
        frame_count++;
        if (frame_count % 30 == 0) // Every ~1 second at 30fps
        {
            stabilization_time--;
            printf("   Stabilizing... %d seconds remaining\n", stabilization_time);
        }
        
        usleep(33333); // ~30fps
    }

    printf("✅ Device stabilized (%d frames processed)\n", frame_count);

    // Now cleanly shut down (same as camtest)
    printf("🔄 Shutting down cleanly...\n");
    
    freenect_stop_depth(fn_dev);
    freenect_stop_video(fn_dev);
    freenect_close_device(fn_dev);
    freenect_shutdown(fn_ctx);

    printf("✅ Device released cleanly\n");
    printf("🎯 Device is now ready for Python scripts!\n");
    printf("   You can now run your Python freenect scripts.\n");

    return 0;
}
