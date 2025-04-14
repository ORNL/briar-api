
EVAL_DIR=/Users/2r6/Projects/briar/briar-evaluation
EVAL_PHASE=phase2
PROTOCOL_TYPE=validation
PROTOCOL=4.2.0
EVAL_PATH=$EVAL_DIR/$EVAL_PHASE/briar_$PROTOCOL_TYPE_v$PROTOCOL

PROBE_SIGSET=$EVAL_PATH/validation_probe.xml
GALLERY1_SIGSET=$EVAL_PATH/
python -m briar sigset-enroll --progress --database validation_4.2.0_probe --entry-type probe --max-frames 40 --no-save /Users/2r6/Projects/briar/briar-evaluation/evaluation/phase2/briar_validation_v4.2.0/validation_probe.xml /Users/2r6/briarrd/