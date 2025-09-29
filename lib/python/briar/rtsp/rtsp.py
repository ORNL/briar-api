import gi
# import required library like Gstreamer and GstreamerRtspServer
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, frame_queue, frame_batch_size, **properties):
        super(SensorFactory, self).__init__(**properties)
        self.frame_queue = frame_queue
        self.number_frames = 0
        self.fps = 0
        self.frame_batch_size = frame_batch_size

    def on_need_data(self, src, lenght):

        #Skip a frame if the RTSP stream is getting too far behind the BRIAR processing stream (slight difference in FPS speed even when set the same)
        if self.frame_batch_size == 0:
            frames_behind_over_batch_size = self.frame_queue.qsize() - (self.fps * 15)    
        else:
            frames_behind_over_batch_size = self.frame_queue.qsize() - self.frame_batch_size
        if frames_behind_over_batch_size > 0:
            print(f"skipping a frame to try to help catch up")
            try:
                self.frame_queue.get_nowait()
            except:
                pass

        #Push a frame to RTSP steram
        frame = self.frame_queue.get()
        data = frame.tostring()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.duration = self.duration
        timestamp = self.number_frames * self.duration
        buf.pts = buf.dts = int(timestamp)
        buf.offset = timestamp
        self.number_frames += 1
        retval = src.emit('push-buffer', buf)
        if retval != Gst.FlowReturn.OK:
            print(retval)

    #Called by DisplayManager once FPS and Resolution is determined
    def set_stream_options(self, fps, width, height):
        if self.fps != fps:
            self.fps = fps
            self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
            self.launch_string = (
                            'appsrc name=source is-live=true block=true do-timestamp=true format=GST_FORMAT_TIME '
                            'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 '
                            '! videoconvert ! videorate ! video/x-raw,format=I420,framerate={}/1 '
                            '! x264enc speed-preset=ultrafast tune=zerolatency '
                            '   bitrate=1500 key-int-max={} bframes=0 ref=1 aud=true '
                            '   vbv-buf-capacity=1500 option-string=scenecut=0:open-gop=0 '
                            '! h264parse config-interval=-1 '
                            '! video/x-h264,stream-format=byte-stream,alignment=au,profile=constrained-baseline '
                            '! queue max-size-time=0 max-size-bytes=0 max-size-buffers=30 leaky=downstream '
                            '! rtph264pay name=pay0 pt=96 config-interval=-1 mtu=1200 aggregate-mode=none'
                        ).format(width, height, self.fps, self.fps, self.fps * 3)
            print(f"RTSP stream server started at {width}x{height} resolution and {self.fps} fps")

    #Called when new RTSP client connects
    def do_create_element(self, url):
        if self.fps == 0:
            print("RTSP server not ready yet")
            return
        return Gst.parse_launch(self.launch_string)

    #Called when new RTSP client connects
    def do_configure(self, rtsp_media):
        print("CONFIGURE AGAIN")
        if self.fps == 0:
            print("RTSP server not ready yet")
            return
    
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)



class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, frame_queue, rtsp_stream_port,rtsp_user,rtsp_pass,frame_batch_size, **properties):
        super(GstServer, self).__init__(**properties)
        self.factory = SensorFactory(frame_queue=frame_queue, frame_batch_size=frame_batch_size)
        self.set_service(rtsp_stream_port)
        self.factory.set_shared(True)

        #Add authentication parameters if requested by client
        if rtsp_user != "" or rtsp_pass != "":
            perms = GstRtspServer.RTSPPermissions.new()
            perms.add_permission_for_role("user", "media.factory.access", True)
            perms.add_permission_for_role("user", "media.factory.construct", True)
            self.factory.set_permissions(perms)  # apply to this mount/factory. 

            auth = GstRtspServer.RTSPAuth.new()
            token = GstRtspServer.RTSPToken.new()
            token.set_string("media.factory.role", "user")            # attach the "user" role to this credential
            basic = GstRtspServer.RTSPAuth.make_basic(rtsp_user, rtsp_pass) # builds "user:pass" Basic token
            auth.add_basic(basic, token)                              # register the login
            self.set_auth(auth)

        self.get_mount_points().add_factory("/searchstream", self.factory)
        self.attach(None)