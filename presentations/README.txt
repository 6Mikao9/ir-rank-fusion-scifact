展示文件

reading-slides.tex：论文阅读展示，10页，约10分钟。
reading-讲稿.txt：逐页时间安排、完整中文讲稿、出处与答疑。
project-slides.tex：Project展示，10页，含本次实际实验结果。
project-讲稿.txt：逐页时间安排、完整中文讲稿、出处与答疑。

编译
使用XeLaTeX，每份运行两次以解析总页数：
  xelatex -interaction=nonstopmode reading-slides.tex
  xelatex -interaction=nonstopmode reading-slides.tex
  xelatex -interaction=nonstopmode project-slides.tex
  xelatex -interaction=nonstopmode project-slides.tex

Overleaf：分别上传源码，以XeLaTeX为编译器。使用TeX Live自带Fandol中文字体。
默认隐藏来源notes，观众看到10页正文。每页来源保留在源码的note中，外部讲稿也附有来源。
标题页使用课程作业署名，未填写姓名、学号。可直接编辑author，不需要访问私有信息目录。
Project数值取自results/metrics.json、paired_bootstrap.json、environment.json、tuning.json。
GitHub远程仓库尚未创建，最终课程如要求代码链接，应另行补入真实仓库URL。
