import cv2
import matplotlib
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar
import briar.grpc_json as grpc_json
from briar.media_converters import image_proto2cv,image_proto2np
import pyvision as pv
import os
import math
import matplotlib.pyplot as plt
import briar.media
import cv2
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.patches import Circle
from matplotlib.offsetbox import (TextArea, DrawingArea, OffsetImage,
                                  AnnotationBbox)
from matplotlib.cbook import get_sample_data


def visualize_matches(matches_path):
    print('viz on ',matches_path)
    matches_object = grpc_json.load(matches_path)

    probe_detections = matches_object.probe_detections
    similarities = matches_object.similarities
    assert len(probe_detections) == len(similarities)

    probe_image = briar.media.decodeMedia(matches_object.probe_media)

    probe_faces = []
    probe_matches = []
    all_matchims = []
    for i,det in enumerate(probe_detections):
        r = det.location
        r = (r.x,r.y,r.x+r.width,r.y+r.height)
        probe_chip = probe_image[r[1]:r[3],r[0]:r[2]]
        cv2.rectangle(probe_image,(r[0],r[1]),(r[2],r[3]),(0,0,255),4)
        probe_faces.append(probe_chip)
        matchlist = matches_object.similarities[i].match_list
        matchims = []
        matchims.append(probe_chip)
        for matchinfo in matchlist:
            resultim = briar.media.decodeMedia(matchinfo.record.view)
            det = matchinfo.record.detection.location
            matchims.append(resultim[det.y:det.y+det.height,det.x:det.x+det.width])
        all_matchims.append(matchims)
    if len(all_matchims) > 0:
        max_matches = np.array([len(matchims) for matchims in all_matchims]).max()


        w = 100
        h = 100

        fig8 = plt.figure(constrained_layout=False,figsize=(25,6))
        nrows = max(len(probe_faces),3)
        ncols = max_matches+int(max_matches*.25)
        print('ncols:',ncols,nrows)
        querywidth = ncols-max_matches
        print('querywidht',querywidth)
        gs1 = fig8.add_gridspec(nrows=nrows, ncols=ncols, left=0.05, right=1, wspace=0.05)
        f8_ax1 = fig8.add_subplot(gs1[:, :querywidth])
        f8_ax1.imshow(probe_image[:,:,::-1])
        for row in range(len(probe_faces)):
            matchlist = matches_object.similarities[row].match_list
            matchims = all_matchims[row]
            for col in range(max_matches):
                if col < len(matchims):
                    entry_id = ''
                    if col > 0:
                        matchinfo = matchlist[col-1]
                        entry_id = matchinfo.record.entry_id[:8]
                    img = cv2.resize(matchims[col], (w, h))[:, :, ::-1]
                    f8_ax2 = fig8.add_subplot(gs1[row, col+querywidth])
                    f8_ax2.imshow(img)
                    f8_ax2.xaxis.set_visible(False)
                    f8_ax2.yaxis.set_visible(False)
                    if col > 0:
                        s=float("{0:.2f}".format(matchlist[col-1].score))
                        f8_ax2.text(0.5, -0.2,   entry_id + "-" +str(s), ha="center",transform=f8_ax2.transAxes)
        plt.show()


def decode_track(tracklet,framenum=None,newsource=None):

    id = tracklet.tracklet_id
    frames= []

    if framenum == "center":
        targetframe = int(len(tracklet.detections)/2)
    elif framenum is not None:
        targetframe = framenum
    if newsource:

        cap = cv2.VideoCapture(newsource)
        numframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        print('decoding new source ', newsource)
    frame_i = 0
    for i,det in enumerate(tracklet.detections):

        if not framenum or (framenum and i == targetframe):
            if not newsource:
                im = briar.media.decodeMedia(det.media)[:,:,::-1]
                frames.append(im[:, :, ::-1])
            else:
                curframe= cap.get(cv2.CAP_PROP_POS_FRAMES)
                if not i == curframe:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, min(numframes - 1, i))
                ret,frame = cap.read()
                if frame is not None:
                    im = frame[det.location.y:det.location.height+det.location.y,det.location.x:det.location.width+det.location.x]
                    frames.append(im[:,:,::-1])
    return frames


def visualize_track(track_path,options):
    track_object = grpc_json.load(track_path)

    if options.verbose:
        print('track ',os.path.basename(track_path),' contains ', len(track_object), ' tracklets')
        for tracklet in track_object:
            print('\t tracklet ', tracklet.tracklet_id, ' has ', len(tracklet.detections), ' frames')
    for obj in track_object:
        vis = decode_track(obj)
        id = obj.tracklet_id
        for im in vis:
            if im is not None and min(im.shape) > 0:
                cv2.imshow('track '+str(id),im)
                cv2.waitKey(120)



def visualize_detection(detection_path):
    print('unimplemented')
    pass
if __name__ == '__main__':
    # fdir = "/Users/2r6/Projects/briar/FairMOT/videos/MOT16-03.tracklet"
    # fdir = "/Users/2r6/Projects/briar/briar-api/media/test_probe/hillary3.matches"
    # fdir = "/Users/2r6/Projects/briar/briar-api/media/test_probe/obama3.matches"
    fdir = "/Users/2r6/Projects/briar/briar-api/media/test_probe/clinton3.matches"

    # fdir = "/Users/2r6/Projects/briar/briar-api/media/test_probe/manyPresidents.matches"

    # fdir = "/Users/2r6/Projects/briar/briar-api/media/test_gallery/quinten1.matches"
    fdir = "/Users/2r6/Projects/briar/briar-api/media/test_gallery/hillary2.matches"
    if os.path.exists(fdir) and os.path.isdir(fdir):
        files = [os.path.join(fdir,f) for f in os.listdir(fdir)]
    elif os.path.exists(fdir) and os.path.isfile(fdir):
        files = [fdir]

    for f in files:
        if f.endswith('.tracklet'):
            visualize_track(f)
        if f.endswith('.matches'):
            visualize_matches(f)


class match_matrix_visualizer:
    def __init__(self,searchReply,probedbname,gallerydbname):
        self.searchReply = searchReply
        self.probedb_name = probedbname
        self.gallerydb_name = gallerydbname
        self.prevx = None
        self.prevy = None
        self.annotations = {}
        self.figures = {}
        self.fig = None
        self.ax = None
        self.xsources = list(searchReply.match_matrix.column_sources)
        self.ysources = list(searchReply.match_matrix.row_sources)
        self.mat = briar.media_converters.matrix_proto2np(searchReply.match_matrix)
        self.xlabs = list(searchReply.match_matrix.column_headers)
        self.ylabs = list(searchReply.match_matrix.row_headers)
        self.gt = None
    def showmat_interactive(self):
        fig, ax = plt.subplots()
        self.fig = fig
        self.ax = ax
        plt.title("match matrix for " + self.gallerydb_name + " against " + self.probedb_name)
        annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        self.annotations['main'] = annot
        self.annotations['main'].set_visible(False)
        fig.canvas.mpl_connect("button_press_event", lambda event: windowclick(event, self))

        fig.canvas.mpl_connect("motion_notify_event", lambda event: windowhover_filename_only(event, self))
        ax.matshow(self.mat)
        goodx = False
        goody = False
        if len(self.xlabs) == self.mat.shape[1]:
            goodx = True
            plt.xticks(ticks=list(range(self.mat.shape[1])), labels=self.xlabs)
        if len(self.ylabs) == self.mat.shape[0]:
            goody = True
            plt.yticks(ticks=list(range(self.mat.shape[0])), labels=self.ylabs)
        if goodx and goody:
            self.gt = np.zeros(self.mat.shape)
            for i, y in enumerate(self.ylabs):
                self.gt[i] = (np.array(self.xlabs) == y).astype(np.int)

            # plt.matshow(gt)
            # plt.title("ground truth")
            # plt.show()
        plt.show()


def get_frame(vidfile):
    cap = cv2.VideoCapture(vidfile)
    numframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.set(cv2.CAP_PROP_POS_FRAMES,min(numframes-1,20))
    ret, frame = cap.read()
    return frame

def update_annot(ind,visualizer,pltloc,playvid=False):

    # pos = sc.get_offsets()[ind["ind"][0]]
    visualizer.annotations['main'].xy = ind


    if str(ind[0]) in visualizer.searchReply.matrix_probe_tracklets:
        tracklet_probe = visualizer.searchReply.matrix_probe_tracklets[str(ind[0])]
        # attributes = visualizer.searchReply.probe_attributes[str(ind[0])]
        # probe_start_frame = None
        # probe_stop_frame = None
        # for att in attributes:
        #     if att == "start_frame":
        #         probe_start_frame = att.ivalue
        #     if att == "stop_frame":
        #         probe_stop_frame = att.ivalue
        images = decode_track(tracklet_probe,framenum='center',newsource=visualizer.xsources[ind[0]])
        frame = images[0]
    else:
        # arr = np.arange(100).reshape((10, 10))
        frame = get_frame(visualizer.xsources[ind[0]])
    if str(ind[1]) in visualizer.searchReply.matrix_gallery_tracklets:
        tracklet_gallery = visualizer.searchReply.matrix_gallery_tracklets[str(ind[1])]
        # attributes = visualizer.searchReply.gallery_attributes[str(ind[0])]
        images = decode_track(tracklet_gallery,framenum='center',newsource=visualizer.ysources[ind[1]])
        gallery_start_frame = None
        gallery_stop_frame = None
        # print(attributes)
        # for att in attributes:
        #     if att == "start_frame":
        #         gallery_start_frame = att.ivalue
        #     if att == "stop_frame":
        #         gallery_stop_frame = att.ivalue
        frame = images[0]
    else:
        # arr = np.arange(100).reshape((10, 10))
        frame = get_frame(visualizer.xsources[ind[0]])
    text = "{}\n {}".format(visualizer.xsources[ind[0]] ,
                            visualizer.ysources[ind[1]])
    visualizer.annotations['main'].set_text(text)
    croppad = 30
    halfwidth = int(frame.shape[1]/2)
    halfheight = int(frame.shape[0]/2)
    # arr = cv2.resize(frame[halfheight-croppad:halfheight+croppad,halfwidth-croppad:halfwidth+croppad],(30,30))
    arr = cv2.resize(frame,(30,30))
    # playVideo(visualizer.xsources[ind[0]])
    if playvid:
        track1_vid=decode_track(tracklet_probe,newsource=visualizer.xsources[ind[0]])
        track2_vid=decode_track(tracklet_gallery,newsource=visualizer.ysources[ind[1]])

        playVideo([track1_vid,track2_vid],titles=[os.path.basename(visualizer.xsources[ind[0]]),os.path.basename(visualizer.xsources[ind[1]])])
    # arr = cv2.resize(cv2.imread(xsources[ind[0]]),(30,30))
    im = OffsetImage(arr, zoom=2)
    im.image.axes = visualizer.ax
    if 'image' in visualizer.annotations and visualizer.annotations['image'] is not None:
        visualizer.annotations['image'].remove()
    ab = AnnotationBbox(im, xy=ind,
                        xybox=(-50., 50.),
                        xycoords='data',
                        boxcoords="offset points",
                        pad=0.3,
                        arrowprops=dict(arrowstyle="->"))
    visualizer.annotations['image'] = ab
    visualizer.ax.add_artist(ab)


    # ab.set_image(cv2.imread(xsources[ind[0]]))
    # ab.xy = ind
    # annot.get_bbox_patch().set_facecolor(cmap(norm(c[ind["ind"][0]])))
    visualizer.annotations['main'].get_bbox_patch().set_alpha(0.4)
def windowclick(event,visualizer):
    windowhover(event,visualizer,playvid=True)
def windowhover(event,visualizer,playvid=False):
    vis = visualizer.annotations['main'].get_visible()
    x_im = None
    y_im = None
    if event.xdata and event.ydata:
        x_im=math.floor(event.xdata-.5)+1
        y_im=math.floor(event.ydata-.5)+1
    x_window = event.x
    y_window = event.y
    pltloc = x_window,y_window
    # print(x_im,y_im,x_window,y_window)
    if y_im is not None and x_im is not None and ((not y_im == visualizer.prevy and not x_im == visualizer.prevx) or playvid):
        visualizer.prevx = x_im
        visualizer.prevy = y_im
        update_annot((x_im,y_im),visualizer,pltloc,playvid=playvid)
        visualizer.annotations['main'].set_visible(True)
        visualizer.fig.canvas.draw_idle()
    else:
        if vis:
            visualizer.annotations['main'].set_visible(False)
            visualizer.fig.canvas.draw_idle()

def windowhover_filename_only(event,visualizer):
    vis = visualizer.annotations['main'].get_visible()
    x_im = None
    y_im = None
    if event.xdata and event.ydata:
        x_im = math.floor(event.xdata - .5) + 1
        y_im = math.floor(event.ydata - .5) + 1
    x_window = event.x
    y_window = event.y
    pltloc = x_window, y_window
    # print(x_im,y_im,x_window,y_window)
    if y_im is not None and x_im is not None and (
            (not y_im == visualizer.prevy and not x_im == visualizer.prevx) or True):
        visualizer.prevx = x_im
        visualizer.prevy = y_im
        update_annot_filename_only((x_im, y_im), visualizer, pltloc)
        visualizer.annotations['main'].set_visible(True)
        visualizer.fig.canvas.draw_idle()
    else:
        if vis:
            visualizer.annotations['main'].set_visible(False)
            visualizer.fig.canvas.draw_idle()
def update_annot_filename_only(ind,visualizer,pltloc):

    # pos = sc.get_offsets()[ind["ind"][0]]
    visualizer.annotations['main'].xy = ind
    probe_attributes = visualizer.searchReply.matrix_probe_attributes
    gallery_attributes = visualizer.searchReply.matrix_gallery_attributes
    # print(probe_attributes)
    probe_start_frame = None
    probe_stop_frame = None
    for attk in probe_attributes:
        att_list = probe_attributes[attk].attributes
        for att in att_list:
            # print('atti',att)
            if att.key == "start_frame":
                probe_start_frame = att.ivalue
            if att.key == "stop_frame":
                probe_stop_frame = att.ivalue
        print(probe_start_frame,probe_stop_frame)
    probe_attributes = visualizer.searchReply.matrix_probe_attributes[str(ind)].attributes
    gallery_start_frame = None
    gallery_stop_frame = None

    for attk in gallery_attributes:

        att_list = gallery_attributes[attk].attributes
        for att in att_list:
            if att.key == "start_frame":
                gallery_start_frame = att.ivalue
            if att.key == "stop_frame":
                gallery_stop_frame = att.ivalue

    text = "{}\n{}\n{}\n{}".format(os.path.basename(visualizer.xsources[ind[0]]),"start: "+str(probe_start_frame)+" stop:"+str(probe_stop_frame),
                           os.path.basename(visualizer.ysources[ind[1]]),"start: "+str(gallery_start_frame)+" stop:"+str(gallery_stop_frame))
    visualizer.annotations['main'].set_text(text)
    visualizer.annotations['main'].get_bbox_patch().set_alpha(0.4)

def playVideo(vidfiles,titles=None,attributes=None,isvideo=True):
    numfigs = len(vidfiles)
    fig, ax = plt.subplots(1, numfigs)
    if numfigs == 1:
        ax = [ax]
    vids = []

    for i,vidfile in enumerate(vidfiles):
        cd = {}
        if isvideo and isinstance(vidfile,str):
            cap = cv2.VideoCapture(vidfile)
            cd['cap']=cap
            numframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        else:
            numframes = len(vidfile)
            cd['frames'] = vidfile
        cd['numframes'] = numframes
        cd['ax'] = ax[i]
        title = ""
        if titles is not None:
            title = titles[i]

        if attributes is not None:
            for att in attributes:
                if att.key == "start_frame":
                    title += " f " + str(att.ivalue) + " to "
                if att.key == "stop_frame:":
                    title += str(att.ivalue)
        cd['ax'].set_title(title)

        img = None
        cd['img'] = img
        cd['i'] = 0
        vids.append(cd)
    run = 1
    while run:
        run = 0
        for cd in vids:
            numframes = cd['numframes']
            ax = cd['ax']
            if cd['i'] < numframes:
                if 'cap' in cd:
                    cap = cd['cap']
                    ret, im = cap.read()
                else:
                    im = cd['frames'][cd['i']]
                if cd['img'] is None:
                    cd['img'] = ax.imshow(im)
                else:
                    cd['img'].set_data(im)
                cd['i'] += 1
                run += 1
        plt.draw()

        plt.pause(.05)

