/*
 * Kinect Device Bridge
 * 
 * This utility keeps the Kinect device open and provides a simple
 * interface for Python scripts to access it through shared memory
 * or a simple protocol.
 */

#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include "libfreenect.h"

#ifndef SIGQUIT // win32 compat
    #define SIGQUIT SIGTERM
#endif

volatile bool running = true;
void signalHandler(int signal)
{
    if (signal == SIGINT || signal == SIGTERM || signal == SIGQUIT)
    {
        printf("\n🛑 Received signal %d, shutting down...\n", signal);
        running = false;
    }
}

// Global device handle
freenect_context* fn_ctx = NULL;
freenect_device* fn_dev = NULL;

// Shared memory structure for Python communication
typedef struct {
    bool device_ready;
    bool depth_ready;
    bool video_ready;
    int depth_width;
    int depth_height;
    int video_width;
    int video_height;
    char status_message[256];
} kinect_status_t;

kinect_status_t* shared_status = NULL;

void depth_cb(freenect_device *dev, void *depth, uint32_t timestamp)
{
    // Mark depth as ready
    if (shared_status) {
        shared_status->depth_ready = true;
    }
}

void video_cb(freenect_device *dev, void *video, uint32_t timestamp)
{
    // Mark video as ready
    if (shared_status) {
        shared_status->video_ready = true;
    }
}

int main(int argc, char** argv)
{
    printf("🌉 Kinect Device Bridge\n");
    printf("=======================\n");
    
    // Handle signals gracefully
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    signal(SIGQUIT, signalHandler);

    // Create shared memory for status
    int shm_fd = shm_open("/kinect_bridge_status", O_CREAT | O_RDWR, 0666);
    if (shm_fd == -1) {
        perror("shm_open");
        return 1;
    }
    
    if (ftruncate(shm_fd, sizeof(kinect_status_t)) == -1) {
        perror("ftruncate");
        return 1;
    }
    
    shared_status = mmap(NULL, sizeof(kinect_status_t), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (shared_status == MAP_FAILED) {
        perror("mmap");
        return 1;
    }
    
    // Initialize status
    memset(shared_status, 0, sizeof(kinect_status_t));
    strcpy(shared_status->status_message, "Initializing...");

    // Initialize libfreenect
    int ret = freenect_init(&fn_ctx, NULL);
    if (ret < 0)
    {
        printf("❌ Failed to initialize freenect context: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to initialize context");
        return ret;
    }
    printf("✅ Freenect context initialized\n");

    // Show debug messages and use camera only
    freenect_set_log_level(fn_ctx, FREENECT_LOG_DEBUG);
    freenect_select_subdevices(fn_ctx, FREENECT_DEVICE_CAMERA);
    printf("✅ Log level set and camera selected\n");

    // Find out how many devices are connected
    int num_devices = freenect_num_devices(fn_ctx);
    if (num_devices < 0)
    {
        printf("❌ Failed to get device count: %d\n", num_devices);
        strcpy(shared_status->status_message, "Failed to get device count");
        freenect_shutdown(fn_ctx);
        return num_devices;
    }
    if (num_devices == 0)
    {
        printf("❌ No Kinect devices found!\n");
        strcpy(shared_status->status_message, "No devices found");
        freenect_shutdown(fn_ctx);
        return 1;
    }
    printf("✅ Found %d Kinect device(s)\n", num_devices);

    // Open the first device
    ret = freenect_open_device(fn_ctx, &fn_dev, 0);
    if (ret < 0)
    {
        printf("❌ Failed to open device: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to open device");
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Device opened successfully\n");

    // Set depth and video modes
    ret = freenect_set_depth_mode(fn_dev, freenect_find_depth_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_DEPTH_MM));
    if (ret < 0)
    {
        printf("❌ Failed to set depth mode: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to set depth mode");
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Depth mode set\n");

    ret = freenect_set_video_mode(fn_dev, freenect_find_video_mode(FREENECT_RESOLUTION_MEDIUM, FREENECT_VIDEO_RGB));
    if (ret < 0)
    {
        printf("❌ Failed to set video mode: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to set video mode");
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Video mode set\n");

    // Set callbacks
    freenect_set_depth_callback(fn_dev, depth_cb);
    freenect_set_video_callback(fn_dev, video_cb);
    printf("✅ Callbacks set\n");

    // Start depth and video streams
    ret = freenect_start_depth(fn_dev);
    if (ret < 0)
    {
        printf("❌ Failed to start depth stream: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to start depth stream");
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Depth stream started\n");

    ret = freenect_start_video(fn_dev);
    if (ret < 0)
    {
        printf("❌ Failed to start video stream: %d\n", ret);
        strcpy(shared_status->status_message, "Failed to start video stream");
        freenect_stop_depth(fn_dev);
        freenect_close_device(fn_dev);
        freenect_shutdown(fn_ctx);
        return ret;
    }
    printf("✅ Video stream started\n");

    // Update shared status
    shared_status->device_ready = true;
    shared_status->depth_width = 640;
    shared_status->depth_height = 480;
    shared_status->video_width = 640;
    shared_status->video_height = 480;
    strcpy(shared_status->status_message, "Device ready and streaming");

    printf("🎯 Device bridge is running!\n");
    printf("   Device is ready for Python scripts\n");
    printf("   Status available in shared memory: /kinect_bridge_status\n");
    printf("   Press Ctrl+C to stop\n\n");

    // Main event loop
    int frame_count = 0;
    while (running)
    {
        ret = freenect_process_events(fn_ctx);
        if (ret < 0)
        {
            printf("❌ Error processing events: %d\n", ret);
            strcpy(shared_status->status_message, "Error processing events");
            break;
        }
        
        frame_count++;
        if (frame_count % 300 == 0) // Every ~10 seconds at 30fps
        {
            printf("📊 Bridge running... %d frames processed\n", frame_count);
        }
        
        usleep(33333); // ~30fps
    }

    // Clean shutdown
    printf("\n🔄 Shutting down bridge...\n");
    
    shared_status->device_ready = false;
    strcpy(shared_status->status_message, "Shutting down...");
    
    freenect_stop_depth(fn_dev);
    freenect_stop_video(fn_dev);
    freenect_close_device(fn_dev);
    freenect_shutdown(fn_ctx);

    // Clean up shared memory
    munmap(shared_status, sizeof(kinect_status_t));
    close(shm_fd);
    shm_unlink("/kinect_bridge_status");

    printf("✅ Bridge shut down cleanly\n");
    return 0;
}
