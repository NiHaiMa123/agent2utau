"""Pre-mapping coverage questions, sourced outside the 31-word table.

No candidate entity/MEAS IDs here. Musical tasks are authored questions, not
recordings or new labels. Recheck is a process split, never statistical holdout.
"""
DATE = '2026-10-10'
STUDY = 'docs/lastpage-cross-condition-study-20261008.md'
TENC = 'docs/lastpage-tenc-controlled-probe-20261008.md'
SHFC = 'docs/lastpage-shfc-controlled-probe-20261008.md'
ONSET = 'docs/lastpage-shfc-onset-probe-20261008.md'
GUO = 'docs/lastpage-guo-register-probe-20261008.md'
POSITIVE = 'docs/lastpage-guo-positive-comparison-20261008.md'
BREC = 'docs/lastpage-brec-cohort-probe-20261008.md'
PHONE = 'docs/lastpage-guo-phoneme-audit-20261008.md'

WEB_SOURCES = [
 dict(id='ESRC:01',title='Mürbe et al. 2003, Auditory and kinesthetic feedback in singing',
      url='https://www.isca-archive.org/maveba_2003/murbe03_maveba.pdf',
      locator='printed pp183–186; methods/limitations',read_status='full_paper_text_read',
      scope='28起始学生/22复查；三和弦、连/断、快/慢和反馈遮蔽；不是听者混音掩蔽模型，也不迁移人体训练因果到模型'),
 dict(id='ESRC:02',title='Jansens, Bloothooft & de Krom 1997, Perception and acoustics of emotions in singing',
      url='https://www.isca-archive.org/eurospeech_1997/jansens97_eurospeech.pdf',
      locator='printed pp2155–2158; material, perception, regression cautions',read_status='full_paper_text_read',
      scope='同一德语乐句/14专业歌手/25听者；多情绪及评分差异，只用于任务/标签边界，不套系数或中文情绪公式'),
 dict(id='ESRC:03',title='Kob & Neuschaefer-Rube 2003, Acoustic analysis of overtone singing',
      url='https://www.isca-archive.org/maveba_2003/kob03_maveba.pdf',
      locator='printed pp187–190; introduction/methods',read_status='selected_fulltext_sections_read',
      scope='一个sygyt演唱者的谱/超声/阻抗观察；不是独立双F0或所有撕裂唱法真值'),
 dict(id='ESRC:04',title='UNSW formant/resonance/pole distinction',
      url='https://www.phys.unsw.edu.au/jw/formant.html',locator='high-F0 example and object distinction',
      read_status='component_explanation_read',scope='作者实验室对象与可辨识性解释；非新歌唱样本'),
 dict(id='ESRC:05',title='Praat Voice breaks',url='https://praat.org/manual/Voice_1__Voice_breaks.html',
      locator='continuous sustained vowel and locally unvoiced distinctions',
      read_status='component_method_conditions_read',scope='持续元音方法，不把正常辅音/休止或检测失败都叫破音'),
 dict(id='ESRC:06',title='Praat jitter/shimmer conditions',
      url='https://praat.org/manual/PointProcess__Get_jitter__local____.html',
      locator='period and pair selection; D source for shimmer separately retained',
      read_status='inherited_D_component_read_not_reexecuted',scope='周期级测量条件提问，无新的录音、pulse或临床阈值'),
]

# code, description, local report, evidence key, label text/status, role, shared group
USER_CASES = [
 ('U01','1:27果原版，uo/E4，同字问题侧',STUDY,'current-word-112','偏假/往上顶','baseline_problem','initial-position-feedback'),
 ('U02','3:04抱原版，ao/B4，同字问题侧',STUDY,'current-word-225','偏假/往上顶','baseline_problem','initial-position-feedback'),
 ('U03','1:33之原版，ir/F#4，相对偏实侧',STUDY,'current-word-124','偏实','relative_reference','initial-position-feedback'),
 ('U04','2:56只原版，ir/A4，相对偏实侧',STUDY,'current-word-214','偏实','relative_reference','initial-position-feedback'),
 ('U05','约3:17果原版，相同MIDI64跨上下文',POSITIVE,'OBS-001','中间这个可以','local_usable','guo-three-comparison'),
 ('U06','3:04抱C，145ms进入的局部可用变体',ONSET,'RESP-003','可以','local_usable','bao-onset-acceptance'),
 ('U07','抱TENC取消，数值响应但未感知区别',TENC,'RESP-001','没啥区别','no_difference','tenc-feedback'),
 ('U08','抱SHFC初B，更实且字头破音',SHFC,'RESP-002','更实了，但是有破音的情况；抱的字头','benefit_with_side_effect','shfc-b-feedback'),
 ('U09','约1:14/3:04/3:31原抱的相似性定位',TENC,'same_bao_original_vocal','我听着都一样','similarity_only','bao-three-comparison'),
 ('U10','果SHFC B与邻字这：无改善且响度下降',GUO,'RESP-004','果字没啥区别，这的咬字好像也没啥区别，而且引入新的问题，响度下降','no_benefit_with_side_effect','guo-shfc-feedback'),
 ('U11','BREC -10：1:27问题果',BREC,'RESP-005','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U12','BREC -10：1:33偏实之',BREC,'RESP-006','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U13','BREC -10：2:56偏实只',BREC,'RESP-007','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U14','BREC -10：3:04问题抱',BREC,'RESP-008','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U15','BREC -10：3:17可用果',BREC,'RESP-009','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U16','BREC -10：已接受抱C',BREC,'RESP-010','全部没区别','no_difference','brec-six-shared-feedback'),
 ('U17','约3:44果，MIDI64；第三段未获标签',POSITIVE,'word-282-at-224.132s','unknown','unknown_control','guo-three-comparison'),
 ('U18','318字中313字未获原版听感标签的集合',STUDY,'313-unlabeled-words','unknown','unknown_population','cross-condition-study'),
]

# Independent musical-task questions authored from plan requirements, not table
# descriptor counterexamples. No claim these movements occur in existing audio.
MUSIC_CASES = [
 ('M01','长音保持直音，稳定可为有意；是否错误需音乐目标','stable,intended,body,long'),
 ('M02','一整句渐强至重音，再回落；单字平均无法保存组织','changing,intended,phrase,level'),
 ('M03','弱收尾、硬切与尾混响三种候选；可听收声关系','changing,tail,release'),
 ('M04','上行滑音到目标，保留到达身份/参照，不把全部弯曲叫异常','changing,intended,transition,pitch'),
 ('M05','下行滑音/尾滑，源音与目的音、字尾和后字关系','changing,intended,tail,pitch'),
 ('M06','字头倚音/上挑后到正音，迟到可能有意','changing,onset,intended,reference'),
 ('M07','一字跨多音melisma；多note不能多算歌词核','changing,same_vowel,body,multi_note'),
 ('M08','跨辅音/元音的连唱；正常换型与声线断层分开','changing,consonant,vowel,phrase,legato'),
 ('M09','断唱与合法休止；中断并非必定破音','changing,intended,staccato,gap'),
 ('M10','短时快速转音/颤音两目标交替，不能把所有周期当vibrato','changing,intended,short,ornament'),
 ('M11','颤音晚进入/退出且速率深度变化；与AM/谱变化分开','changing,body,entry,exit'),
 ('M12','同一频率在不同调式/和声/参照下的音准意义','stable,reference,harmony,phrase'),
]

LITERATURE_CASES = [
 ('L01','ESRC:01','连/断与快/慢三和弦任务；短音的测量支持区别','task,short,long,legato,staccato'),
 ('L02','ESRC:01','演唱者听觉反馈被遮蔽；与听者混音清晰度区分','masking,performer_feedback,mix'),
 ('L03','ESRC:02','同一乐句中性/怒/喜/惧/悲的多标签感知任务','intended,emotion,phrase'),
 ('L04','ESRC:02','相同呈现的听者评分差异/多情绪并存','listener,uncertainty,emotion'),
 ('L05','ESRC:03','sygyt低持续音与被增强谐波旋律；双音听感未必双独立源','low,high,intended,overtone'),
 ('L06','ESRC:04','高F0谐波稀疏时共振不可辨识的例','high,vowel,unknown,resonance'),
 ('L07','ESRC:05','持续元音声断检测条件，正常清辅音/休止/失败的反查','consonant,body,gap,unknown'),
 ('L08','ESRC:06','滑音/强AM与pulse jitter/shimmer的尺度混淆','changing,cycle,unknown'),
]

AUTHOR_CASES = [
 ('A01','huahai','花海作者note21的+续音：输入延展结构，不推听感','same_vowel,multi_note,structure'),
 ('A02','yuai','雨爱作者重复de，在不同tone/duration的输入上下文','same_syllable,context,structure'),
 ('A03','lastpage','作者最后一页AP/SP、note间隙及多part；结构不证明实际呼吸','phrase,gap,structure'),
 ('A04','all','三作者工程不同谱面音区；不是实测F0或高音质量标签','low,high,structure,unknown'),
]

RECHECK = {'M10','M12','L04','L05','L07','A04'}


def cases():
    rows=[]
    for code,text,report,evidence,label,role,group in USER_CASES:
        rows.append(dict(id='CASE:E'+code,description=text,origin='existing_user_evidence',
            role=role,source_refs=[report],evidence_key=evidence,label_text=label,
            label_kind='reported_summary' if code in {'U01','U02','U03','U04'} else
                'joined_two_user_messages' if code=='U08' else 'verbatim' if label!='unknown' else 'unknown',
            shared_evidence_group=group,tags=['regression','existing_feedback'] if label!='unknown' else ['unknown','existing_material']))
    for code,text,tags in MUSIC_CASES:
        rows.append(dict(id='CASE:E'+code,description=text,origin='authored_music_task_question',
            role='unrecorded_task_question',source_refs=['plan.md#E'],evidence_key='no_recording',
            label_text='unknown',label_kind='unknown',shared_evidence_group='music-task-design',tags=tags.split(',')))
    for code,source,text,tags in LITERATURE_CASES:
        rows.append(dict(id='CASE:E'+code,description=text,origin='original_research_task' if code<='L05' else 'method_failure_condition',
            role='external_task_scope_no_local_audio',source_refs=[source],evidence_key='published_task_not_imported_audio',
            label_text='unknown',label_kind='unknown',shared_evidence_group=source,tags=tags.split(',')))
    for code,project,text,tags in AUTHOR_CASES:
        rows.append(dict(id='CASE:E'+code,description=text,origin='author_input_structure',
            role='read_only_structure_not_audio_label',source_refs=['research/baishuo/manifest.json'],
            evidence_key=project,label_text='unknown',label_kind='unknown',shared_evidence_group='author-originals',tags=tags.split(',')))
    for r in rows:
        r['review_partition']='deferred_mapping_recheck' if r['id'][6:] in RECHECK else 'main_mapping'
        r['no_new_audio_or_labels']=True
    assert len(rows)==42 and len({r['id'] for r in rows})==42
    assert sum(r['review_partition']=='deferred_mapping_recheck' for r in rows)==6
    return rows
