import pysam as ps
from sys import argv

bam_filepath = argv[1]
fixed_bam_filepath = argv[2]

with ps.AlignmentFile(bam_filepath, "rb") as bam, ps.AlignmentFile(fixed_bam_filepath, "wb", template=bam) as fixed_bam:
    for read in bam:
        if read.next_reference_name == None:
            read.mate_is_unmapped = True  # sets 0x8 (MUNMAP)
        fixed_bam.write(read)

ps.index(fixed_bam_filepath)

