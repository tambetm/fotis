export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/hpc_tambet/libjpeg/lib

python /home/hpc_tambet/cuda-convnet2/convnet.py --save-path /storage/hpc_tambet/fotis --data-provider fotis --inner-size 48 --test-range 4 --train-range 0-3 --data-path /storage/hpc_tambet/fotis/isikud_batches_64x64_gray_996_49 --gpu 0 --layer-def ~/fotis/layers/layers-fotis-imagenet-gray-49.cfg --layer-params ~/fotis/layers/layer-params-fotis-imagenet.cfg --epochs 1000
