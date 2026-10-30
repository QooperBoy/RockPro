using System;
using System.Globalization;

namespace RockPro.CAD {
    // Millimetres; footprint is the full rigid mounting envelope, not its cutout.
    public static class MountRowLayout {
        static bool Finite(double x){return !Double.IsNaN(x)&&!Double.IsInfinity(x);}
        static string Mm(double x){return x.ToString("0.##",CultureInfo.GetCultureInfo("pl-PL"));}
        public static int Capacity(double length,double width,double gap,double margin){
            if(!Finite(length)||!Finite(width)||!Finite(gap)||!Finite(margin)||width<=0||gap<0||margin<0)return 0;
            return (int)Math.Max(0,Math.Min(Int32.MaxValue,Math.Floor((length-2*margin+gap+1e-7)/(width+gap))));
        }
        public static string Validate(double count,int minimum,int slots,double length,double center,double spread,double width,double gap,double margin){
            if(!Finite(count)||!Finite(length)||!Finite(center)||!Finite(spread)||!Finite(width)||!Finite(gap)||!Finite(margin)||width<=0||gap<0||margin<0||length<=0||spread<0)
                return "Nieprawidłowe wymiary, odstępy lub liczba okuć.";
            if(Math.Abs(count-Math.Round(count))>1e-8||count<minimum)
                return "Wpisz całkowitą liczbę nie mniejszą niż "+minimum+".";
            int capacity=Capacity(length,width,gap,margin);
            if(count>capacity)
                return "Brak miejsca: "+Mm(count)+" × "+Mm(width)+" + "+Mm(count-1)+" × "+Mm(gap)+" + 2 × "+Mm(margin)+" > "+Mm(length)+" mm. Maksymalnie "+capacity+" szt. przy tych marginesach i odstępach.";
            if(count>slots)return "Miejsce pozwala na "+capacity+" szt., ale model ma przygotowane "+slots+" wystąpienia. Wymagana rozbudowa modelu.";
            int n=(int)Math.Round(count);if(n==0)return null;
            double span=n>1?spread:0;
            if(center-span/2-width/2<margin-1e-7||center+span/2+width/2>length-margin+1e-7)
                return "Rząd wychodzi poza dostępną ściankę. Popraw środek lub rozstaw; wymagany margines "+Mm(margin)+" mm.";
            if(n>1&&spread/(n-1)<width+gap-1e-7)
                return "Za mały rozstaw skrajnych osi: potrzeba co najmniej "+Mm((n-1)*(width+gap))+" mm dla "+n+" szt. Maksymalnie "+(1+(int)Math.Floor((spread+1e-7)/(width+gap)))+" szt. przy obecnym rozstawie.";
            return null;
        }
    }
}
